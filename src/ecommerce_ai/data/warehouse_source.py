"""真实数仓适配器（占位）。

接入示例：在 .env 设 DATA_SOURCE=warehouse，然后实现下方方法。
例如连接 StarRocks / ClickHouse / Postgres / Hive，把 query/schema 落到对应引擎。
业务代码（Agent、API、前端）无需任何改动。
"""
from __future__ import annotations

import pandas as pd

from ecommerce_ai.core.models import DatasetInfo, QueryResult
from ecommerce_ai.data.source import DataSource


class WarehouseSource(DataSource):
    def __init__(self) -> None:
        raise NotImplementedError(
            "请实现 WarehouseSource：在 .env 设 DATA_SOURCE=warehouse 并完成 query/schema 等方法。"
        )

    def query(self, sql: str, limit: int = 1000) -> QueryResult:
        raise NotImplementedError

    def list_tables(self) -> list[str]:
        raise NotImplementedError

    def schema_text(self, table: str = "") -> str:
        raise NotImplementedError

    def table_info(self, name: str) -> dict:
        raise NotImplementedError

    def ingest_dataframe(self, df: pd.DataFrame, table_name: str) -> DatasetInfo:
        raise NotImplementedError

    def datasets(self) -> list[DatasetInfo]:
        raise NotImplementedError

    def read_table(self, name: str) -> pd.DataFrame:
        raise NotImplementedError
