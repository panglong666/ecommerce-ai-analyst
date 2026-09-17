"""RAG 检索工具。"""
from __future__ import annotations

from ecommerce_ai.rag.retriever import retrieve


def search_knowledge(query: str, top_k: int | None = None, domain: str = "") -> list[dict]:
    """混合检索知识库，返回 [{'text','source','score'}, ...]。

    domain 为空表示全库检索；指定时只在该知识域内检索（域隔离）。
    """
    return retrieve(query, top_k, domain=domain)
