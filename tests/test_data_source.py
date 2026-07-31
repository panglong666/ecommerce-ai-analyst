"""数据源适配器测试。"""
from ecommerce_ai.data.mock_source import MockSource


def test_validate_sql_rejects_writes():
    src = MockSource()
    assert src.validate_sql("DROP TABLE orders") is not None
    assert src.validate_sql("DELETE FROM orders") is not None
    assert src.validate_sql("INSERT INTO orders VALUES (1)") is not None
    assert src.validate_sql("SELECT 1") is None
    assert src.validate_sql("WITH t AS (SELECT 1) SELECT * FROM t") is None


def test_schema_text_is_str():
    src = MockSource()
    assert isinstance(src.schema_text(), str)
