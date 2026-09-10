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


# 分组类语义提示词（用于退化检测是否值得重试）
_GROUP_HINTS = ("排行", "排名", "各", "分类", "品类", "对比", "分别", "按", "top", "Top", "TOP")
_MIN_GROUPS = 2


def _is_degenerate(question: str, columns: list, rows: list) -> str | None:
    """检测分组退化（结果无区分度）。非分组类问题返回 None（单结果正常）。"""
    if not any(h in question for h in _GROUP_HINTS):
        return None
    if not rows:
        return "结果为空，可能分组维度或筛选条件有误"
    grp = columns[0] if columns else None
    if grp:
        distinct = {r.get(grp) for r in rows}
        if len(distinct) < _MIN_GROUPS:
            return f"结果仅返回 {len(distinct)} 个分组（列 '{grp}' 取值={list(distinct)}），缺乏区分度"
    if len(rows) < _MIN_GROUPS:
        return f"结果仅 {len(rows)} 行，疑似分组维度选择不当"
    return None


def nl2sql_node(state: AgentState) -> AgentState:
    schema = get_schema_text(state.get("dataset", ""))
    q = state["question"]
    prompt = render_prompt(load_prompt("nl2sql"), schema=schema, question=q)
    sql = _strip_fences(chat(prompt))
    result = run_sql(sql)
    if result.error:
        # 一次自动重试：把错误反馈给 LLM
        retry_prompt = (
            f"上一条 SQL 执行报错：{result.error}\n请修正后重新生成一条只读 SQL。\n"
            f"schema:\n{schema}\n问题：{q}\n只输出 SQL。"
        )
        sql = _strip_fences(chat(retry_prompt))
        result = run_sql(sql)
    # X4 兜底：分组退化检测 → 一次重选（反问前置已拦截大部分歧义，此为残余安全网）
    reason = _is_degenerate(q, result.columns, result.rows)
    if reason and not result.error:
        hint = (
            f"上次查询存在问题：{reason}。\n"
            f"请重新生成 SQL：选择 schema 中区分度最高的维度列作为分组列，确保返回多个分组。"
            f"\nschema:\n{schema}\n问题：{q}\n只输出 SQL。"
        )
        sql = _strip_fences(chat(hint))
        result = run_sql(sql)
    return {
        "sql": result.sql or sql,
        "columns": result.columns,
        "rows": result.rows,
        "error": result.error or "",
    }
