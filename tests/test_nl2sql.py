"""NL2SQL Agent 测试（MockLLM 回退下也能跑通流程）。"""
from ecommerce_ai.agents.graph import run


def test_run_returns_response():
    resp = run("各品类销售额排行")
    assert resp.question == "各品类销售额排行"
    assert resp.route in ("nl2sql", "rag", "error")
    assert isinstance(resp.answer, str)


def test_run_handles_empty_db():
    resp = run("任意问题")
    assert resp.elapsed_ms >= 0
