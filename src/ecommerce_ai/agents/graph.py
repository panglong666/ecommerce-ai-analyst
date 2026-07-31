"""LangGraph 编排：supervisor 路由 -> NL2SQL/Viz/Interpret 或 RAG。"""
from __future__ import annotations

import time

from langgraph.graph import END, START, StateGraph

from ecommerce_ai.agents.nodes.interpret import interpret_node
from ecommerce_ai.agents.nodes.nl2sql import nl2sql_node
from ecommerce_ai.agents.nodes.rag_node import rag_node
from ecommerce_ai.agents.nodes.supervisor import supervisor_node
from ecommerce_ai.agents.nodes.viz import viz_node
from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.core.models import AgentResponse, ChartSpec

_compiled = None


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("nl2sql", nl2sql_node)
    g.add_node("viz", viz_node)
    g.add_node("interpret", interpret_node)
    g.add_node("rag", rag_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        lambda s: s.get("route", "nl2sql"),
        {"nl2sql": "nl2sql", "rag": "rag"},
    )
    g.add_edge("nl2sql", "viz")
    g.add_edge("viz", "interpret")
    g.add_edge("interpret", END)
    g.add_edge("rag", END)
    return g.compile()


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run(question: str) -> AgentResponse:
    """对外统一入口：输入问题，返回结构化响应。"""
    t0 = time.time()
    out = get_graph().invoke({"question": question})
    elapsed = int((time.time() - t0) * 1000)
    chart = out.get("chart")
    return AgentResponse(
        question=question,
        route=out.get("route", "nl2sql"),
        sql=out.get("sql", ""),
        columns=out.get("columns", []),
        rows=out.get("rows", []),
        chart=ChartSpec(**chart) if chart else None,
        answer=out.get("answer", ""),
        sources=out.get("sources", []),
        elapsed_ms=elapsed,
    )
