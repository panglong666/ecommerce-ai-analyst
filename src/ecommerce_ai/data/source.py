"""数据源抽象接口。真实数仓只需实现同一接口即可替换 Mock。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
import sqlglot
from sqlglot import exp

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
    def schema_text(self, table: str = "") -> str:
        """供 NL2SQL 使用的 schema 文本描述。table 指定时只返回该表。"""

    @abstractmethod
    def table_info(self, name: str) -> dict[str, Any]:
        """单张表的字段信息。"""

    @abstractmethod
    def ingest_dataframe(self, df: pd.DataFrame, table_name: str) -> DatasetInfo:
        """把 DataFrame 落库为新表（上传场景）。"""

    @abstractmethod
    def datasets(self) -> list[DatasetInfo]:
        """已注册的数据集列表。"""

    @abstractmethod
    def read_table(self, name: str) -> "pd.DataFrame":
        """读取整张表为 DataFrame（画像 / 基线构建用）。"""

    # 注：sqlglot 中 TRUNCATE / REPLACE 等不具独立节点类，
    # TRUNCATE 归入 Drop，REPLACE INTO 归入 Insert（kind=REPLACE），故无需单列。
    _FORBIDDEN_NODES = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
        exp.Create, exp.Merge,
    )

    def validate_sql(self, sql: str) -> str | None:
        """只允许只读 SELECT（含 WITH 公共表表达式）；返回错误信息或 None。

        基于 sqlglot 做 AST 白名单解析，杜绝关键词黑名单的各类绕过：
        - 多语句（分号拼接）：parse 返回多条语句，直接拒绝
        - 注释混淆（SEL/**/ECT）、大小写变形：AST 解析天然免疫
        - 递归 CTE：可能制造无限循环（DoS），明确拒绝
        - 任意写 / DDL / DML 子句：AST 遍历兜底拦截
        """
        s = (sql or "").strip()
        if not s:
            return "SQL 为空"
        try:
            statements = [st for st in sqlglot.parse(s, read="sqlite") if st is not None]
        except Exception:
            return "SQL 语法无法解析（仅支持标准 SELECT 查询）"
        if len(statements) != 1:
            return "仅允许单条查询语句"
        stmt = statements[0]
        if not isinstance(stmt, exp.Select):
            return "仅允许 SELECT 或 WITH...SELECT 只读查询"
        # 递归 CTE 可能无限循环（DoS），禁止：
        # 1) WITH 节点显式带 recursive 标志；2) 某个 CTE 被自身引用（自引用）
        with_nodes = [n for n in stmt.walk() if isinstance(n, exp.With)]
        for w in with_nodes:
            if getattr(w, "recursive", False):
                return "不支持递归 CTE 查询"
            cte_names = {c.alias for c in w.expressions if isinstance(c, exp.CTE)}
            for col in stmt.walk():
                if isinstance(col, exp.Column) and col.table in cte_names:
                    return "不支持递归 CTE 查询"
        # 兜底：拦截任何写 / DDL / DML 节点
        for node in stmt.walk():
            if isinstance(node, self._FORBIDDEN_NODES):
                return "禁止的 SQL 操作（仅允许只读 SELECT）"
        return None

    def enforce_limit(self, sql: str, hard_limit: int = 1000) -> str:
        """强制硬 LIMIT 以防笛卡尔积 / 大结果集拖垮服务。

        仅当 SQL 本身没有 LIMIT 时才重写，避免改动已合规的查询。
        """
        try:
            parsed = sqlglot.parse_one(sql, read="sqlite")
        except Exception:
            return sql
        if not isinstance(parsed, exp.Select):
            return sql
        if parsed.args.get("limit") is not None:
            return sql  # 已有 LIMIT，原样返回
        try:
            return parsed.limit(hard_limit).sql(dialect="sqlite")
        except Exception:
            return sql


def get_data_source() -> DataSource:
    """根据配置返回数据源实例。"""
    from ecommerce_ai.core.config import settings

    if settings.data_source == "warehouse":
        from ecommerce_ai.data.warehouse_source import WarehouseSource

        return WarehouseSource()
    from ecommerce_ai.data.mock_source import MockSource

    return MockSource()
