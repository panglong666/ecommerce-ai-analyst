"""LLM 工厂：DeepSeek（OpenAI 兼容）或 MockLLM 回退。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ecommerce_ai.core.config import settings


class MockLLM:
    """无 API Key 时的回退，保证流程可演示。"""

    _MOCK_SQL = (
        "SELECT category, ROUND(SUM(amount),2) AS sales "
        "FROM orders GROUP BY category ORDER BY sales DESC;"
    )

    def invoke(self, prompt: Any, **kwargs: Any) -> SimpleNamespace:
        text = self._guess(str(prompt))
        return SimpleNamespace(content=text)

    def stream(self, prompt: Any, **kwargs: Any):
        text = self._guess(str(prompt))
        for ch in text:
            yield SimpleNamespace(content=ch)

    @staticmethod
    def _guess(prompt: str) -> str:
        low = prompt.lower()
        if "只输出一个词" in prompt or "意图" in prompt:
            return "nl2sql"
        if "sql" in low or "select" in low or "查询" in prompt:
            return MockLLM._MOCK_SQL
        if "结论" in prompt or "建议" in prompt or "解读" in prompt:
            return "（Mock）华东区羽绒服上月销售额 ¥1,280 万，同比 +23.5%，跑赢大盘；建议加大华东仓备货。"
        return "（Mock 模式）未配置 DEEPSEEK_API_KEY，这是示例回复。配置 Key 后即可调用真实大模型。"


def get_llm():
    """返回一个带 .invoke(prompt)->obj(.content) 的 LLM。"""
    use_mock = (settings.llm_provider == "mock") or (not settings.deepseek_api_key)
    if use_mock:
        if settings.llm_provider != "mock" and not settings.deepseek_api_key:
            print("[LLM] 未配置 DEEPSEEK_API_KEY，使用 MockLLM 回退。填 .env 后即可切真实模型。")
        return MockLLM()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )


def chat(prompt: str) -> str:
    """统一调用入口：返回纯文本。"""
    llm = get_llm()
    resp = llm.invoke(prompt)
    return getattr(resp, "content", str(resp))


_PROMPTS_DIR = settings.project_root / "configs" / "prompts"


def load_prompt(name: str) -> str:
    """读取 configs/prompts/{name}.txt。"""
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def render_prompt(template: str, **kwargs: Any) -> str:
    """简单占位渲染：{key} -> value。"""
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
