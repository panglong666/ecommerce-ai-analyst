"""数据源抽象接口。真实数仓只需实现同一接口即可替换 Mock。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from ecommerce_ai.core.models import DatasetInfo, QueryResult


class DataSource(ABC):
    """所有数据源的统一契约。"""

    @abstractmethod
    def query(self, sql: str, limit: int = 1000) -> QueryResult:
        """执行只读 SQL，返回结构化结果。"""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """列出可查的表。"""

    @abstractmethod
    def schema_text(self) -> str:
        """供 NL2SQL 使用的 schema 文本描述。"""

    @abstractmethod
    def table_info(self, name: str) -> dict[str, Any]:
        """单张表的字段信息。"""

    @abstractmethod
    def ingest_dataframe(self, df: pd.DataFrame, table_name: str) -> DatasetInfo:
        """把 DataFrame 落库为新表（上传场景）。"""

    @abstractmethod
    def datasets(self) -> list[DatasetInfo]:
        """已注册的数据集列表。"""

    def validate_sql(self, sql: str) -> str | None:
        """只允许只读 SELECT；返回错误信息或 None。"""
        s = sql.strip().lower()
        forbidden = ("insert", "update", "delete", "drop", "alter", "truncate", "create", "replace", "attach", "pragma")
        for w in forbidden:
            if w in s:
                return f"禁止的 SQL 操作: {w}（仅允许 SELECT）"
        if not s.startswith("select") and not s.startswith("with"):
            return "仅允许 SELECT 或 WITH 开头的只读查询"
        return None


def get_data_source() -> DataSource:
    """根据配置返回数据源实例。"""
    from ecommerce_ai.core.config import settings

    if settings.data_source == "warehouse":
        from ecommerce_ai.data.warehouse_source import WarehouseSource

        return WarehouseSource()
    from ecommerce_ai.data.mock_source import MockSource

    return MockSource()
