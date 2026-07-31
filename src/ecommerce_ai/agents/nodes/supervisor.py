"""意图路由节点：判断走 NL2SQL 还是 RAG。"""
from __future__ import annotations

from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.llm.factory import chat, load_prompt


def supervisor_node(state: AgentState) -> AgentState:
    instruction = load_prompt("supervisor")
    resp = chat(f"{instruction}\n问题：{state['question']}").strip().lower()
    route = "rag" if "rag" in resp else "nl2sql"
    print(f"[agent] route -> {route}  (question: {state['question'][:40]})")
    return {"route": route}
