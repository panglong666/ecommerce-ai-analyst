"""RAG 节点：检索知识 + 生成带引用的回答。"""
from __future__ import annotations

from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.llm.factory import chat, load_prompt, render_prompt
from ecommerce_ai.tools.rag_tool import search_knowledge


def rag_node(state: AgentState) -> AgentState:
    docs = search_knowledge(state["question"])
    context = "\n---\n".join(f"[{d.get('source', '')}] {d.get('text', '')}" for d in docs) or "（知识库暂无相关内容）"
    prompt = render_prompt(load_prompt("rag"), context=context, question=state["question"])
    answer = chat(prompt)
    sources = [d.get("source", "") for d in docs if d.get("source")]
    return {"answer": answer, "sources": sources}
