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
    reason: str = ""  # 选图理由（可解释，前端可展示）


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
    clarification: list[dict[str, Any]] = Field(default_factory=list)  # 反问选项（分组歧义时）


class DatasetInfo(BaseModel):
    name: str
    rows: int
    columns: list[str]
    source: str = "mock"


class DataProfile(BaseModel):
    """数据画像：自动识别的结构化描述，驱动预警模式选择。"""
    time_col: str | None = None
    metric_cols: list[str] = Field(default_factory=list)
    dim_cols: list[str] = Field(default_factory=list)
    row_count: int = 0
    time_range_days: int | None = None
    granularity: str | None = None  # day / hour / None
    mode: str = "cross_section"  # cross_section / weak_temporal / temporal / full_temporal
    notes: list[str] = Field(default_factory=list)


class AlertItem(BaseModel):
    """单条预警。"""
    metric: str = ""
    metric_label: str = ""
    dimension: str = ""  # 如 "品类=连衣裙" 或 "整体"
    value: float | None = None
    expected: float | None = None
    deviation: str = ""  # 人类可读偏离描述
    level: str = "P2"  # P0 / P1 / P2
    mode: str = ""
    confidence: str = "中"  # 高 / 中 / 低
    message: str = ""
    drill_question: str = ""  # 点「深入归因」时直接发给分析 Agent 的问题


class AlertScanResponse(BaseModel):
    """一次预警扫描的完整响应。"""
    dataset: str = ""
    mode: str = ""
    monitoring: str = ""  # 前端徽标文本
    notes: list[str] = Field(default_factory=list)
    anomalies: list[AlertItem] = Field(default_factory=list)
    advice: str = ""
    scanned: int = 0
