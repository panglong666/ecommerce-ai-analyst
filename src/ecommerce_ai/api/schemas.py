"""API 请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    mode: str = "auto"  # auto / analysis / knowledge
    dataset: str = ""   # 空=全部表(demo)；指定表名=只分析该表


class UploadResponse(BaseModel):
    success: bool
    message: str = ""
    dataset: dict | None = None


class AlertScanRequest(BaseModel):
    dataset: str = ""  # 空=选默认表
    sensitivity: str = "standard"  # conservative / standard / sensitive
    time_col: str | None = None  # 留空=自动识别
    metric_cols: list[str] | None = None  # 留空=自动识别
    dim_cols: list[str] | None = None  # 留空=自动识别
