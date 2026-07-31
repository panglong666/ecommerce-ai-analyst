"""Mock 数据源：本地 SQLite，开箱即跑。"""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from ecommerce_ai.core.config import settings
from ecommerce_ai.core.models import DatasetInfo, QueryResult
from ecommerce_ai.data.source import DataSource


class MockSource(DataSource):
    def __init__(self) -> None:
        self.path = settings.abs(settings.sqlite_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.path}")

    def query(self, sql: str, limit: int = 1000) -> QueryResult:
        err = self.validate_sql(sql)
        if err:
            return QueryResult(sql=sql, error=err)
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(sql), conn)
            rows = df.head(limit).to_dict(orient="records")
            return QueryResult(
                sql=sql,
                columns=list(df.columns),
                rows=rows,
                row_count=len(df),
            )
        except Exception as e:  # noqa: BLE001
            return QueryResult(sql=sql, error=str(e))

    def list_tables(self) -> list[str]:
        return inspect(self.engine).get_table_names()

    def table_info(self, name: str) -> dict[str, Any]:
        cols = inspect(self.engine).get_columns(name)
        return {"name": name, "columns": [{"name": c["name"], "type": str(c["type"])} for c in cols]}

    def schema_text(self) -> str:
        lines: list[str] = []
        for t in self.list_tables():
            info = self.table_info(t)
            cols = ", ".join(f"{c['name']} {c['type']}" for c in info["columns"])
            lines.append(f"表 {t}({cols})")
        return "\n".join(lines) if lines else "（数据库为空，请先运行 sample_data 造数）"

    def _count(self, table: str) -> int:
        try:
            with self.engine.connect() as conn:
                return int(pd.read_sql(text(f"SELECT COUNT(*) AS n FROM {table}"), conn).iloc[0, 0])
        except Exception:  # noqa: BLE001
            return -1

    def ingest_dataframe(self, df: pd.DataFrame, table_name: str) -> DatasetInfo:
        df.to_sql(table_name, self.engine, if_exists="replace", index=False)
        return DatasetInfo(
            name=table_name,
            rows=len(df),
            columns=list(df.columns),
            source="mock",
        )

    def datasets(self) -> list[DatasetInfo]:
        return [
            DatasetInfo(
                name=t,
                rows=self._count(t),
                columns=[c["name"] for c in self.table_info(t)["columns"]],
                source="mock",
            )
            for t in self.list_tables()
        ]
