"""RAG 加载器测试（避免初始化 Chroma，保证快速稳定）。"""
from ecommerce_ai.rag.loader import load_text


def test_load_txt(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("hello world", encoding="utf-8")
    assert load_text(p) == "hello world"


def test_load_csv(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,2\n3,4", encoding="utf-8")
    text = load_text(p)
    assert "a" in text and "1" in text
