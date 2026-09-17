"""数据源适配器测试。"""
from ecommerce_ai.data.mock_source import MockSource


def test_validate_sql_rejects_writes():
    src = MockSource()
    assert src.validate_sql("DROP TABLE orders") is not None
    assert src.validate_sql("DELETE FROM orders") is not None
    assert src.validate_sql("INSERT INTO orders VALUES (1)") is not None
    assert src.validate_sql("SELECT 1") is None
    assert src.validate_sql("WITH t AS (SELECT 1) SELECT * FROM t") is None


def test_validate_sql_allows_readonly_set_ops():
    """集合运算（UNION/INTERSECT/EXCEPT）属只读，应放行；写/多语句/递归仍拒。"""
    src = MockSource()
    assert src.validate_sql("SELECT 1 UNION ALL SELECT 2") is None
    assert src.validate_sql("SELECT 1 INTERSECT SELECT 2") is None
    assert src.validate_sql("SELECT 1 EXCEPT SELECT 2") is None
    # 顶层 UNION 带 ORDER BY 也应放行
    assert src.validate_sql("SELECT a FROM t UNION SELECT b FROM u ORDER BY 1") is None
    # 底线不变：多语句 / 递归 CTE / 写操作
    assert src.validate_sql("SELECT 1; SELECT 2") is not None
    assert src.validate_sql(
        "WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM t WHERE n < 5) SELECT * FROM t"
    ) is not None
    assert src.validate_sql("DELETE FROM t") is not None
    assert src.validate_sql("DROP TABLE t") is not None


def test_enforce_limit_covers_set_ops():
    """放行集合运算后，安全阀也要能给 UNION 加 LIMIT。"""
    src = MockSource()
    out = src.enforce_limit("SELECT 1 AS x UNION ALL SELECT 2", hard_limit=1000)
    assert "LIMIT" in out.upper()
    out2 = src.enforce_limit("SELECT 1 AS x LIMIT 5", hard_limit=1000)
    assert "LIMIT 5" in out2.upper()


def test_schema_text_is_str():
    src = MockSource()
    assert isinstance(src.schema_text(), str)
