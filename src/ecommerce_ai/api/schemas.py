"""API 请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    mode: str = "auto"  # auto / analysis / knowledge


class UploadResponse(BaseModel):
    success: bool
    message: str = ""
    dataset: dict | None = None
