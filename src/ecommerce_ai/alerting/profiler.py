"""数据画像：从任意上传表自动识别时间列 / 指标列 / 维度列并选定监测模式。

这是「通用」的关键——不写死任何表名或字段名，靠列名与采样值
推断结构，再按时间跨度选择对应的检测算法。
"""
from __future__ import annotations

import re

import pandas as pd

from ecommerce_ai.alerting.config import ID_COL_HINTS, TIME_COL_HINTS
from ecommerce_ai.core.models import DataProfile

_ID_RE = re.compile("|".join(ID_COL_HINTS), re.I)
_TIME_RE = re.compile("|".join(TIME_COL_HINTS), re.I)


def _looks_like_time(series: pd.Series) -> float:
    """返回该列可解析为日期行数的比例（0~1）。"""
    if series.dtype.kind in "iu":  # 纯整数不可能是日期
        return 0.0
    s = series.dropna().astype(str).head(50)
    if s.empty:
        return 0.0
    parsed = pd.to_datetime(s, errors="coerce", format="mixed")
    return float(parsed.notna().mean())


def _detect_time_col(df: pd.DataFrame) -> str | None:
    best, best_ratio = None, 0.5
    for c in df.columns:
        if _TIME_RE.search(str(c)) and _looks_like_time(df[c]) > 0.5:
            return c
        r = _looks_like_time(df[c])
        if r > best_ratio:
            best, best_ratio = c, r
    return best


def _detect_metric_cols(df: pd.DataFrame, time_col: str | None) -> list[str]:
    cols: list[str] = []
    for c in df.columns:
        if c == time_col or _ID_RE.search(str(c)):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            nunique = df[c].nunique(dropna=True)
            # 排除高基数（疑似 ID）的数值列
            if nunique > max(50, 0.9 * len(df)):
                continue
            cols.append(c)
    return cols


def _detect_dim_cols(df: pd.DataFrame, time_col: str | None, metric_cols: list[str]) -> list[str]:
    cols: list[str] = []
    for c in df.columns:
        if c == time_col or c in metric_cols:
            continue
        if (pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])
                or str(df[c].dtype).startswith("category")):
            nunique = df[c].nunique(dropna=True)
            if 1 < nunique <= max(20, 0.5 * len(df)):
                cols.append(c)
    return cols


def profile_table(
    df: pd.DataFrame,
    time_col: str | None = None,
    metric_cols: list[str] | None = None,
    dim_cols: list[str] | None = None,
) -> DataProfile:
    """对上传表做结构画像，并选定监测模式。"""
    notes: list[str] = []
    tcol = time_col
    if tcol is None:
        tcol = _detect_time_col(df)
        if tcol:
            notes.append(f"自动识别时间列：{tcol}")
    else:
        notes.append(f"使用指定时间列：{tcol}")

    mcols = metric_cols
    if mcols is None:
        mcols = _detect_metric_cols(df, tcol)
        if mcols:
            notes.append(f"自动识别指标列：{', '.join(mcols)}")
        else:
            notes.append("未识别到数值指标列")

    dcols = dim_cols
    if dcols is None:
        dcols = _detect_dim_cols(df, tcol, mcols)
        if dcols:
            notes.append(f"自动识别维度列：{', '.join(dcols)}")

    time_range_days = None
    granularity = None
    if tcol and tcol in df.columns:
        ts = pd.to_datetime(df[tcol], errors="coerce").dropna()
        if len(ts) >= 2:
            span = (ts.max() - ts.min()).days
            time_range_days = max(span, 1)
            diffs = ts.sort_values().diff().dropna().dt.total_seconds()
            med = diffs.median() if not diffs.empty else 0
            granularity = "hour" if med and med < 86400 else "day"

    if not tcol or time_range_days is None or time_range_days < 1:
        mode = "cross_section"
        notes.append("无可用时间列或仅单日 → 启用【截面对比】模式")
    elif time_range_days < 14:
        mode = "weak_temporal"
        notes.append(f"时间跨度 {time_range_days} 天(<14) → 启用【弱时序】模式(置信低)")
    elif time_range_days >= 365:
        mode = "full_temporal"
        notes.append("时间跨度≥1年 → 启用【完整时序】模式(含同比/季节豁免)")
    else:
        mode = "temporal"
        notes.append(f"时间跨度 {time_range_days} 天 → 启用【标准时序】模式")

    return DataProfile(
        time_col=tcol,
        metric_cols=mcols,
        dim_cols=dcols,
        row_count=len(df),
        time_range_days=time_range_days,
        granularity=granularity,
        mode=mode,
        notes=notes,
    )
