"""歧义判定与反问生成（反问优先，schema 无关）。

给定问题与带样本的 schema，判断分组意图是否歧义；歧义时产出带真实列名+
样本的选项交用户选择，由人最终定夺——不依赖任何列名/语言/取值假设。
"""
from __future__ import annotations

import json
import re

from ecommerce_ai.llm.factory import chat, load_prompt, render_prompt
from ecommerce_ai.tools.sql_tool import get_schema_text


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出里容错提取首个 JSON 对象。"""
    if not text:
        return None
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL)
    if m:
        t = m.group(1)
    else:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            t = t[s:e + 1]
    try:
        obj = json.loads(t)
    except (ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def assess_clarification(question: str, dataset: str = "") -> dict | None:
    """歧义时返回 {'message','options':[{label,question,column}]}，否则 None。

    失败时（Mock 模式/解析异常）返回 None，保证主流程不受影响。
    """
    schema = get_schema_text(dataset)
    prompt = render_prompt(load_prompt("clarify"), schema=schema, question=question)
    try:
        obj = _extract_json(chat(prompt))
    except Exception:  # noqa: BLE001
        return None
    if not obj or not obj.get("ambiguous"):
        return None
    options = obj.get("options") or []
    if not options:
        return None
    clean = []
    for o in options[:4]:
        col = o.get("column") or ""
        q = o.get("question") or (f"{question}，按{col}分组" if col else question)
        clean.append({"label": o.get("label") or col or "选项", "question": q, "column": col})
    return {"message": obj.get("message", "你的意思更接近于哪种分组？"), "options": clean}
