"""混合检索：BM25（字符级，免 jieba）+ 向量相似，融合后取 top_k。"""
from __future__ import annotations

from typing import Any

from rank_bm25 import BM25Okapi

from ecommerce_ai.core.config import settings

_corpus_cache: dict[str, list] | None = None


def _load_corpus() -> dict[str, list]:
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    from ecommerce_ai.rag.vectorstore import get_vectorstore

    data = get_vectorstore().get(include=["documents", "metadatas"])
    _corpus_cache = {
        "ids": list(data.get("ids", [])),
        "texts": list(data.get("documents", [])),
        "metas": list(data.get("metadatas", [])),
    }
    return _corpus_cache


def reset_corpus_cache() -> None:
    global _corpus_cache
    _corpus_cache = None


def retrieve(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.top_k
    corpus = _load_corpus()
    if not corpus["texts"]:
        return []

    # BM25（字符级切分，适配中文，无需额外依赖）
    tokenized = [list(t) for t in corpus["texts"]]
    bm25 = BM25Okapi(tokenized)
    bm_scores = bm25.get_scores(list(query))
    bm_idx = sorted(range(len(bm_scores)), key=lambda i: bm_scores[i], reverse=True)[: k * 2]

    combined: dict[str, dict[str, Any]] = {}
    for i in bm_idx:
        t = corpus["texts"][i]
        meta = corpus["metas"][i] or {}
        combined[t] = {"text": t, "source": meta.get("source", ""), "score": float(bm_scores[i])}

    # 向量召回
    try:
        from ecommerce_ai.rag.vectorstore import get_vectorstore

        vec = get_vectorstore().similarity_search_with_relevance_scores(query, k=k * 2)
        for doc, sc in vec:
            t = doc.page_content
            if t in combined:
                combined[t]["score"] += float(sc)
            else:
                combined[t] = {"text": t, "source": doc.metadata.get("source", ""), "score": float(sc)}
    except Exception as e:  # noqa: BLE001
        print(f"[rag] 向量召回失败，仅用 BM25: {e}")

    ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:k]
    return ranked
