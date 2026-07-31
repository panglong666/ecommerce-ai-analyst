"""可视化节点：根据结果生成 ECharts 配置。"""
from __future__ import annotations

import numbers
from typing import Any

from ecommerce_ai.agents.state import AgentState


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


def build_chart(columns: list[str], rows: list[dict]) -> dict | None:
    if not rows or not columns:
        return None
    x_col = columns[0]
    y_cols = [c for c in columns if c != x_col and _is_numeric(rows, c)]
    if not y_cols:
        return {"chart_type": "table", "option": {"columns": columns, "rows": rows[:100]}}
    chart_type = "line" if _looks_like_timeseries(x_col) else "bar"
    option = {
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
    return {"chart_type": chart_type, "option": option}


def _looks_like_timeseries(col: str) -> bool:
    low = col.lower()
    return any(k in low for k in ("date", "month", "day", "time", "日期", "月"))


def viz_node(state: AgentState) -> AgentState:
    chart = build_chart(state.get("columns", []), state.get("rows", []))
    return {"chart": chart}
