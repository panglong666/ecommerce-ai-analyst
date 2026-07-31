"""数据契约（pydantic 模型）。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """SQL 查询结果。"""
    sql: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None


class ChartSpec(BaseModel):
    """前端 ECharts 配置（直接交给 ECharts setOption）。"""
    chart_type: str = "bar"  # bar / line / pie / table / none
    option: dict[str, Any] = Field(default_factory=dict)


class Interpretation(BaseModel):
    text: str = ""
    sources: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """一次对话的完整响应。"""
    question: str
    route: str = "nl2sql"  # nl2sql / rag
    sql: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    chart: Optional[ChartSpec] = None
    answer: str = ""
    sources: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0
    tokens: Optional[int] = None


class DatasetInfo(BaseModel):
    name: str
    rows: int
    columns: list[str]
    source: str = "mock"
