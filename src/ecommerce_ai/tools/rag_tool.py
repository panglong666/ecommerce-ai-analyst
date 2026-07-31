"""RAG 检索工具。"""
from __future__ import annotations

from ecommerce_ai.rag.retriever import retrieve


def search_knowledge(query: str, top_k: int | None = None) -> list[dict]:
    """混合检索知识库，返回 [{'text','source','score'}, ...]。"""
    return retrieve(query, top_k)
