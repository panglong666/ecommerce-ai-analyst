"""LangGraph 编排：supervisor 路由 -> NL2SQL/Viz/Interpret 或 RAG。"""
from __future__ import annotations

import asyncio
import time

from langgraph.graph import END, START, StateGraph

from ecommerce_ai.agents.nodes.interpret import interpret_node
from ecommerce_ai.agents.nodes.nl2sql import nl2sql_node
from ecommerce_ai.agents.nodes.rag_node import rag_node
from ecommerce_ai.agents.nodes.supervisor import supervisor_node
from ecommerce_ai.agents.nodes.viz import viz_node
from ecommerce_ai.agents.nodes.clarify import assess_clarification
from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.core.models import AgentResponse, ChartSpec

_compiled = None

# 答案重放节奏（秒/块）。仅用于在浏览器侧形成“打字机”流式观感；
# 真实 LLM 本身有生成延迟，此节奏额外开销可忽略；Mock 模式下让流式可见。
ANSWER_PACE = 0.02
_ANSWER_CHUNK = 2  # 每块字符数（中文按字、英文按词感切分）


def _chunk_text(s: str, size: int = _ANSWER_CHUNK):
    """把文本切成小块，供逐块流式重放。"""
    for i in range(0, len(s), size):
        yield s[i : i + size]


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


def run(question: str, dataset: str = "", mode: str = "auto") -> AgentResponse:
    """对外统一入口：输入问题，返回结构化响应。dataset 指定时只分析该表。

    反问优先：分析类问题先判定分组意图是否歧义，歧义则直接返回选项交用户确认，
    不替用户瞎猜——对未知/重命名/多语言 schema 天然稳健。
    """
    t0 = time.time()
    # 反问前置（知识类问题跳过，避免无谓调用）
    if mode != "knowledge":
        try:
            clarify = assess_clarification(question, dataset)
        except Exception:  # noqa: BLE001
            clarify = None
        if clarify:
            return AgentResponse(
                question=question,
                route="clarify",
                answer=clarify["message"],
                clarification=clarify["options"],
                elapsed_ms=int((time.time() - t0) * 1000),
            )
    out = get_graph().invoke({"question": question, "dataset": dataset})
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


async def stream_run(question: str, dataset: str = "", mode: str = "auto"):
    """对话流式入口：逐节点产出 SSE 事件（route/sql/rows/chart/answer/done）。

    与 run() 共享反问前置逻辑；graph 用 astream 按节点推进，前端可增量渲染。
    事件字典统一含 type 字段，便于前端分发。
    """
    t0 = time.time()
    if mode != "knowledge":
        try:
            clarify = assess_clarification(question, dataset)
        except Exception:  # noqa: BLE001
            clarify = None
        if clarify:
            yield {"type": "clarify", "message": clarify["message"], "options": clarify["options"]}
            return

    final: dict = {
        "question": question,
        "route": "nl2sql",
        "sql": "",
        "columns": [],
        "rows": [],
        "chart": None,
        "answer": "",
        "sources": [],
    }
    async for chunk in get_graph().astream({"question": question, "dataset": dataset}):
        for node, update in chunk.items():
            if not isinstance(update, dict):
                continue
            if node == "supervisor" and "route" in update:
                final["route"] = update["route"]
                yield {"type": "route", "route": final["route"]}
            elif node == "nl2sql":
                if "sql" in update and update.get("sql"):
                    final["sql"] = update["sql"]
                    yield {"type": "sql", "sql": final["sql"]}
                if "columns" in update or "rows" in update:
                    final["columns"] = update.get("columns", final["columns"])
                    final["rows"] = update.get("rows", final["rows"])
                    yield {
                        "type": "rows",
                        "columns": final["columns"],
                        "rows": final["rows"],
                    }
            elif node == "viz" and "chart" in update and update.get("chart"):
                final["chart"] = update["chart"]
                yield {"type": "chart", "chart": final["chart"]}
            elif node in ("interpret", "rag") and "answer" in update:
                final["answer"] = update["answer"]
                if node == "rag" and "sources" in update:
                    final["sources"] = update["sources"]
                # 不在此整块推答案；改为下方逐块重放，形成可见的打字机流式

    # 逐块重放最终答案：服务端按 SSE 分片推送，前端边收边渲染 -> 真·流式
    answer_text = final.get("answer") or ""
    if answer_text:
        yield {"type": "answer_start"}
        for piece in _chunk_text(answer_text):
            yield {"type": "answer_delta", "text": piece}
            await asyncio.sleep(ANSWER_PACE)

    final["elapsed_ms"] = int((time.time() - t0) * 1000)
    yield {
        "type": "done",
        "response": {
            "question": final["question"],
            "route": final["route"],
            "sql": final["sql"],
            "columns": final["columns"],
            "rows": final["rows"],
            "chart": final["chart"],
            "answer": final["answer"],
            "sources": final["sources"],
            "elapsed_ms": final["elapsed_ms"],
        },
    }
