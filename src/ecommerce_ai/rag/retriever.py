"""混合检索：BM25（字符级，免 jieba）+ 向量相似，融合后取 top_k。

支持按知识域（domain）限定检索范围，避免不相关业务域的文档混入；
并对「同一文档贡献的片段数」设上限，防止长文档霸占 top_k（多产品混检时尤为重要）。
"""
from __future__ import annotations

from typing import Any

from rank_bm25 import BM25Okapi

from ecommerce_ai.core.config import settings

# 按 domain 缓存语料；"" / None 表示全库
_corpus_cache: dict[str, dict] = {}
# 同一文档最多贡献的片段数，保证检索结果的多样性
_MAX_PER_SOURCE = 2


def _load_corpus(domain: str = "") -> dict[str, list]:
    key = domain or "__all__"
    if key in _corpus_cache:
        return _corpus_cache[key]
    from ecommerce_ai.rag.vectorstore import get_vectorstore

    store = get_vectorstore()
    if domain:
        data = store.get(where={"domain": domain}, include=["documents", "metadatas"])
    else:
        data = store.get(include=["documents", "metadatas"])
    _corpus_cache[key] = {
        "ids": list(data.get("ids", [])),
        "texts": list(data.get("documents", [])),
        "metas": list(data.get("metadatas", [])),
    }
    return _corpus_cache[key]


def reset_corpus_cache() -> None:
    global _corpus_cache
    _corpus_cache = {}


def retrieve(query: str, top_k: int | None = None, domain: str = "") -> list[dict[str, Any]]:
    k = top_k or settings.top_k
    corpus = _load_corpus(domain)
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

    # 向量召回（同一域内）
    try:
        from ecommerce_ai.rag.vectorstore import get_vectorstore

        kwargs = {"filter": {"domain": domain}} if domain else {}
        vec = get_vectorstore().similarity_search_with_relevance_scores(query, k=k * 2, **kwargs)
        for doc, sc in vec:
            t = doc.page_content
            if t in combined:
                combined[t]["score"] += float(sc)
            else:
                combined[t] = {"text": t, "source": doc.metadata.get("source", ""), "score": float(sc)}
    except Exception as e:  # noqa: BLE001
        print(f"[rag] 向量召回失败，仅用 BM25: {e}")

    ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    # 多样性控制：同一文档最多 _MAX_PER_SOURCE 块
    out: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    for r in ranked:
        s = r.get("source", "")
        if per_source.get(s, 0) >= _MAX_PER_SOURCE:
            continue
        per_source[s] = per_source.get(s, 0) + 1
        out.append(r)
        if len(out) >= k:
            break
    return out
