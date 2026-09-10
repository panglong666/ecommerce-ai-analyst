"""可视化节点：LLM 初选图表类型 + 规则护栏兜底，生成 ECharts 配置。

设计：原 build_chart 的纯规则逻辑保留为「护栏/兜底」，永远在最后生效；
新增 _llm_choose_chart 让大模型根据问题语义 + 数据特征自行决定图表类型，
再经 _safe_build 做结构合法性与语义硬约束校验，任一步不过就回退规则版。
"""
from __future__ import annotations

import json
import numbers
import re
from typing import Any

from ecommerce_ai.agents.state import AgentState
from ecommerce_ai.llm.factory import chat, load_prompt, render_prompt


def _is_numeric(rows: list[dict], col: str) -> bool:
    for r in rows[:20]:
        v = r.get(col)
        if v is None or v == "":
            continue
        return isinstance(v, numbers.Number)
    return False


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _looks_like_timeseries(col: str) -> bool:
    low = col.lower()
    return any(k in low for k in ("date", "month", "day", "time", "日期", "月"))


def _values_look_dates(rows: list[dict], col: str) -> bool:
    for r in rows[:20]:
        v = r.get(col)
        if v is None or v == "":
            continue
        s = str(v)
        # 形如 2024-01 / 2024-01-15 / 202401 / 2024/1
        return bool(re.search(r"\d{4}[-/]\d{1,2}", s)) or bool(re.fullmatch(r"\d{6,8}", s))
    return False


# ---------------------------------------------------------------------------
# 规则版（护栏兜底，原逻辑保留，不直接删除）
# ---------------------------------------------------------------------------

def build_chart(columns: list[str], rows: list[dict]) -> dict | None:
    if not rows or not columns:
        return None
    x_col = columns[0]
    y_cols = [c for c in columns if c != x_col and _is_numeric(rows, c)]
    if not y_cols:
        return {
            "chart_type": "table",
            "option": {"columns": columns, "rows": rows[:100]},
            "reason": "结果无数值列，以表格展示",
        }
    chart_type = "line" if _looks_like_timeseries(x_col) else "bar"
    return {
        "chart_type": chart_type,
        "option": _option_bar_line(chart_type, x_col, y_cols, rows),
        "reason": "按默认规则生成（首列为时间则折线，否则柱状）",
    }


def _option_bar_line(chart_type: str, x_col: str, y_cols: list[str], rows: list[dict]) -> dict:
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": y_cols[:3]},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": [str(r.get(x_col, "")) for r in rows]},
        "yAxis": {"type": "value"},
        "series": [
            {"name": y, "type": chart_type, "data": [_num(r.get(y)) for r in rows]}
            for y in y_cols[:3]
        ],
    }


# ---------------------------------------------------------------------------
# 数据特征 + LLM 初选
# ---------------------------------------------------------------------------

def _col_profile(columns: list[str], rows: list[dict]) -> dict:
    prof = {}
    for c in columns:
        prof[c] = {
            "numeric": _is_numeric(rows, c),
            "timeseries": _looks_like_timeseries(c) or _values_look_dates(rows, c),
            "cardinality": len({r.get(c) for r in rows[:100]}),
        }
    return prof


def _schema_hint(columns: list[str], prof: dict) -> str:
    return ", ".join(
        f"{c}({'数值' if prof[c]['numeric'] else '维度'}"
        f"{',时间' if prof[c]['timeseries'] else ''})"
        for c in columns
    )


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出里容错提取首个 JSON 对象。"""
    if not text:
        return None
    t = text.strip()
    # 优先匹配 ```json ... ``` 围栏
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


def _llm_choose_chart(question: str, sql: str, columns: list[str], rows: list[dict]) -> dict | None:
    prof = _col_profile(columns, rows)
    prompt = render_prompt(
        load_prompt("viz"),
        question=question,
        sql=sql,
        schema_hint=_schema_hint(columns, prof),
        rows_preview=str(rows[:30]),
    )
    return _extract_json(chat(prompt))


# ---------------------------------------------------------------------------
# 护栏 + 构造
# ---------------------------------------------------------------------------

_WHITELIST = {"bar", "line", "pie", "scatter", "table"}


def _build_option(chart_type: str, x_col: str, y_cols: list[str], rows: list[dict], title: str) -> dict:
    if chart_type in ("bar", "line"):
        return _option_bar_line(chart_type, x_col, y_cols, rows)
    if chart_type == "pie":
        y = y_cols[0]
        return {
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"data": [str(r.get(x_col, "")) for r in rows][:12]},
            "series": [{
                "type": "pie",
                "radius": "60%",
                "data": [{"name": str(r.get(x_col, "")), "value": _num(r.get(y))} for r in rows],
            }],
            **({"title": {"text": title}} if title else {}),
        }
    if chart_type == "scatter":
        y1, y2 = y_cols[0], y_cols[1]
        return {
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": y1},
            "yAxis": {"type": "value", "name": y2},
            "series": [{
                "type": "scatter",
                "data": [[_num(r.get(y1)), _num(r.get(y2))] for r in rows],
            }],
            **({"title": {"text": title}} if title else {}),
        }
    # table
    return {"columns": columns, "rows": rows[:100]}


def _safe_build(question: str, sql: str, columns: list[str], rows: list[dict]) -> dict | None:
    decision = _llm_choose_chart(question, sql, columns, rows)
    prof = _col_profile(columns, rows)

    # LLM 没给出可信决策 → 规则兜底
    if not decision:
        return build_chart(columns, rows)

    ct = decision.get("chart_type")
    x = decision.get("x_field")
    ys = decision.get("y_fields") or []

    # 护栏 1：结构合法性
    if ct not in _WHITELIST:
        return build_chart(columns, rows)
    if x not in columns:
        return build_chart(columns, rows)
    if not all(y in columns and prof[y]["numeric"] for y in ys):
        return build_chart(columns, rows)

    # 护栏 2：语义硬约束（防 LLM 抽风）
    if ct == "pie":
        if len(ys) != 1 or prof[x]["cardinality"] > 12:
            # 扇区过多或无单一数值列 → 降级为柱状图
            ct = "bar"
            # 重新挑选数值列
            ys = [c for c in columns if c != x and prof[c]["numeric"]][:3] or ys
    if ct == "scatter" and len(ys) != 2:
        return build_chart(columns, rows)
    if ct == "table" and any(prof[c]["numeric"] for c in columns):
        return build_chart(columns, rows)

    option = _build_option(ct, x, ys, rows, decision.get("title", ""))
    return {"chart_type": ct, "option": option, "reason": decision.get("reason", "LLM 自动选型")}


def viz_node(state: AgentState) -> AgentState:
    chart = _safe_build(
        state.get("question", ""),
        state.get("sql", ""),
        state.get("columns", []),
        state.get("rows", []),
    )
    return {"chart": chart}
