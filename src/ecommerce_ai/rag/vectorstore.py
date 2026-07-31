"""向量库工厂：默认 Chroma（本地文件）。PGVector/Milvus 留适配位。"""
from __future__ import annotations

from typing import Any

from ecommerce_ai.core.config import settings

COLLECTION = "ecommerce_kb"
_vectorstore: Any = None


def get_vectorstore() -> Any:
    """返回 LangChain Chroma 实例（惰性单例）。"""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore
    if settings.vector_store != "chroma":
        raise NotImplementedError(
            f"向量库 {settings.vector_store} 尚未实现，请在 vectorstore.py 接入 PGVector/Milvus。"
        )
    from langchain_chroma import Chroma

    from ecommerce_ai.rag.embedder import get_embedding_function

    path = str(settings.abs(settings.chroma_path))
    _vectorstore = Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embedding_function(),
        persist_directory=path,
    )
    return _vectorstore


def has_documents() -> bool:
    try:
        store = get_vectorstore()
        data = store.get(include=[])
        return len(data.get("ids", [])) > 0
    except Exception:  # noqa: BLE001
        return False
