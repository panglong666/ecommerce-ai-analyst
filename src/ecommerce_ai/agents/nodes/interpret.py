"""解读节点：用中文给业务结论与建议。"""
from __future__ import annotations

from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.llm.factory import chat, load_prompt, render_prompt


def interpret_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {"answer": f"数据查询失败：{state['error']}"}
    rows_preview = state.get("rows", [])[:50]
    prompt = render_prompt(
        load_prompt("interpret"),
        question=state["question"],
        sql=state.get("sql", ""),
        rows=str(rows_preview),
    )
    answer = chat(prompt)
    return {"answer": answer}
