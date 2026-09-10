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
        safe_sql = self.enforce_limit(sql, limit)
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(safe_sql), conn)
            rows = df.head(limit).to_dict(orient="records")
            return QueryResult(
                sql=safe_sql,
                columns=list(df.columns),
                rows=rows,
                row_count=len(df),
            )
        except Exception:  # noqa: BLE001
            return QueryResult(sql=safe_sql, error="查询执行失败，请检查 SQL 或稍后重试")

    def list_tables(self) -> list[str]:
        return inspect(self.engine).get_table_names()

    def table_info(self, name: str) -> dict[str, Any]:
        cols = inspect(self.engine).get_columns(name)
        return {"name": name, "columns": [{"name": c["name"], "type": str(c["type"])} for c in cols]}

    def _schema_samples(self, table: str, k: int = 5, max_cols: int = 50) -> dict[str, dict]:
        """每列：去重样本值 + distinct 计数（供反问 phrasing 与歧义检测，schema 无关）。"""
        try:
            df = self.read_table(table).head(200)
        except Exception:  # noqa: BLE001
            return {}
        out: dict[str, dict] = {}
        for col in list(df.columns)[:max_cols]:
            series = df[col].dropna().astype(str)
            distinct = series.unique().tolist()
            out[col] = {
                "n": len(distinct),
                "samples": distinct[:k],
                "constant": len(distinct) <= 1,
            }
        return out

    def schema_text(self, table: str = "") -> str:
        all_tables = self.list_tables()
        if table:
            if table not in all_tables:
                return f"（未找到数据集 {table}，请用 /datasets 查看可用表）"
            tables = [table]
        else:
            tables = all_tables
        lines: list[str] = []
        for t in tables:
            info = self.table_info(t)
            # 仅指定表时取样，避免全库拉取
            samples = self._schema_samples(t) if table else {}
            col_parts: list[str] = []
            for c in info["columns"]:
                name, ctype = c["name"], c["type"]
                part = f"{name} {ctype}"
                s = samples.get(name)
                if s:
                    if s["constant"]:
                        sample_txt = s["samples"][0] if s["samples"] else "空"
                        part += f" [常量, 仅值:{sample_txt}]"
                    else:
                        part += f" [基数{s['n']}, 示例:{'/'.join(s['samples'])}]"
                col_parts.append(part)
            lines.append(f"表 {t}({', '.join(col_parts)})")
        return "\n".join(lines) if lines else "（数据库为空，请先上传数据）"

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

    def read_table(self, name: str) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql(text(f"SELECT * FROM {name}"), conn)
