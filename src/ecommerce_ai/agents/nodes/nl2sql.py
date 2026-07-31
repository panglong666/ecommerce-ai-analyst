"""NL2SQL 节点：生成 -> 校验 -> 执行。"""
from __future__ import annotations

import re

from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.llm.factory import chat, load_prompt, render_prompt
from ecommerce_ai.tools.sql_tool import get_schema_text, run_sql


def _strip_fences(sql: str) -> str:
    s = sql.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def nl2sql_node(state: AgentState) -> AgentState:
    schema = get_schema_text()
    prompt = render_prompt(load_prompt("nl2sql"), schema=schema, question=state["question"])
    sql = _strip_fences(chat(prompt))
    result = run_sql(sql)
    if result.error:
        # 一次自动重试：把错误反馈给 LLM
        retry_prompt = (
            f"上一条 SQL 执行报错：{result.error}\n请修正后重新生成一条只读 SQL。\n"
            f"schema:\n{schema}\n问题：{state['question']}\n只输出 SQL。"
        )
        sql = _strip_fences(chat(retry_prompt))
        result = run_sql(sql)
    return {
        "sql": result.sql or sql,
        "columns": result.columns,
        "rows": result.rows,
        "error": result.error or "",
    }
