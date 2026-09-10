"""SQL 工具：取数 + schema。"""
from __future__ import annotations

from ecommerce_ai.core.models import QueryResult
from ecommerce_ai.data.source import get_data_source


def get_schema_text(table: str = "") -> str:
    """返回当前数据源的可读 schema，供 NL2SQL 使用。table 指定时只返回该表。"""
    return get_data_source().schema_text(table=table)


def run_sql(sql: str, limit: int = 1000) -> QueryResult:
    """执行只读 SQL 并返回结构化结果。"""
    return get_data_source().query(sql, limit=limit)
