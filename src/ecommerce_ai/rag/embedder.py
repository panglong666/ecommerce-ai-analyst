"""嵌入函数工厂。

默认 chroma_default：使用 Chroma 自带 ONNX MiniLM，无需 torch，开箱即用。
local_bge：BAAI/bge-small-zh-v1.5，中文友好，需 pip install -e .[bge]（含 torch）。
"""
from __future__ import annotations

from typing import Any

from ecommerce_ai.core.config import settings


def get_embedding_function() -> Any:
    provider = settings.embedding_provider
    if provider == "local_bge":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            print(f"[rag] 使用本地 bge 嵌入: {settings.bge_model}")
            return HuggingFaceEmbeddings(model_name=settings.bge_model)
        except Exception as e:  # noqa: BLE001
            print(f"[rag] local_bge 不可用({e})，回退 chroma 默认嵌入。")
            return None
    return None  # None -> Chroma 使用自带默认嵌入
