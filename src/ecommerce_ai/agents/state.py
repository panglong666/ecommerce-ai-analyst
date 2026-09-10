"""LangGraph 共享状态。"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    dataset: str  # 显式指定的分析数据集（表名），空=全部表
    route: str  # nl2sql / rag
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    chart: Optional[dict[str, Any]]
    answer: str
    sources: list[str]
    error: str
