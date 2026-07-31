"""文档索引：加载 -> 切分 -> 向量化 -> 增量 upsert 进 Chroma。"""
from __future__ import annotations

from pathlib import Path

from ecommerce_ai.core.config import settings
from ecommerce_ai.rag.loader import load_text
from ecommerce_ai.rag.retriever import reset_corpus_cache
from ecommerce_ai.rag.vectorstore import get_vectorstore


def index_file(path: str | Path, source_name: str | None = None) -> dict:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text = load_text(path)
    source = source_name or Path(path).name
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_text(text)
    store = get_vectorstore()

    # 增量更新：先删除该来源的旧片段
    try:
        existing = store.get(where={"source": source}, include=[])
        old_ids = existing.get("ids", [])
        if old_ids:
            store.delete(ids=list(old_ids))
    except Exception as e:  # noqa: BLE001
        print(f"[indexer] 清理旧片段跳过: {e}")

    ids = [f"{source}#{i}" for i in range(len(chunks))]
    metas = [{"source": source, "chunk_idx": i} for i in range(len(chunks))]
    store.add_texts(texts=chunks, metadatas=metas, ids=ids)
    reset_corpus_cache()
    print(f"[indexer] 已索引 {source}（{len(chunks)} 片段）")
    return {"source": source, "chunks": len(chunks)}


def index_default_docs() -> int:
    """索引 data/uploads/docs/ 下的示例文档。"""
    docs_dir = settings.abs(settings.upload_dir) / "docs"
    if not docs_dir.exists():
        return 0
    n = 0
    for p in sorted(docs_dir.glob("*")):
        if p.suffix.lower() in (".txt", ".md", ".csv", ".pdf", ".docx"):
            try:
                index_file(p)
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"[indexer] 跳过 {p.name}: {e}")
    return n
