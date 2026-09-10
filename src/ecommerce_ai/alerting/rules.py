"""三套检测器：截面离群 / 时序突变 / 跨次环比。

均使用稳健统计量（中位数 + MAD / 标准差），对小样本与离群点更稳。
每条告警都带 drill_question，供前端一键调分析 Agent 归因。
"""
from __future__ import annotations

import pandas as pd

from ecommerce_ai.alerting.config import (
    CROSS_UPLOAD_DROP,
    MIN_GROUP,
    MIN_TEMPORAL,
    RATE_METRICS,
)
from ecommerce_ai.core.models import AlertItem, DataProfile


def _robust_z(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return s
    med = s.median()
    mad = (s - med).abs().median()
    if mad and mad > 0:
        return (s - med) / (1.4826 * mad)
    std = s.std()
    if std and std > 0:
        return (s - med) / std
    return s * 0.0


def _level(z: float) -> str:
    a = abs(z)
    if a >= 4:
        return "P0"
    if a >= 3:
        return "P1"
    return "P2"


def _group_iter(df: pd.DataFrame, dim_cols: list[str]):
    """生成 (维度键文本, 子DataFrame)；无维度时整体作为一组。"""
    if not dim_cols:
        yield "整体", df
        return
    for key, g in df.dropna(subset=dim_cols).groupby(dim_cols):
        label = key if isinstance(key, str) else "_".join(map(str, key))
        yield label, g


def _aggregate(df: pd.DataFrame, profile: DataProfile, metric: str) -> dict[str, float]:
    """按维度聚合；比率型用均值，其余用求和，与快照侧保持一致。"""
    use_mean = metric in RATE_METRICS
    series_of = lambda g: pd.to_numeric(g[metric], errors="coerce")
    out: dict[str, float] = {}
    for label, g in _group_iter(df, profile.dim_cols):
        s = series_of(g)
        val = s.mean() if use_mean else s.sum()
        if pd.notna(val):
            out[label] = float(val)
    return out


def detect_cross_section(df: pd.DataFrame, profile: DataProfile, z_thresh: float) -> list[AlertItem]:
    """截面离群：在每组内找显著偏离中位数的一行（取最极端的一行）。"""
    items: list[AlertItem] = []
    for metric in profile.metric_cols:
        for label, g in _group_iter(df, profile.dim_cols):
            if len(g) < MIN_GROUP:
                continue
            z = _robust_z(g[metric])
            if z.abs().max() <= z_thresh:
                continue
            idx = z.abs().idxmax()
            val = float(g.loc[idx, metric])
            zv = float(z.loc[idx])
            items.append(AlertItem(
                metric=metric,
                dimension=label,
                value=val,
                expected=float(g[metric].median()),
                deviation=f"组内偏离中位数 {zv:+.1f}σ",
                level=_level(zv),
                mode="cross_section",
                confidence="中",
                message=f"{label} 的 {metric} 为 {val:,.1f}，显著高于同组水平",
                drill_question=f"分析{' ' + label if label != '整体' else ''}的 {metric} 异常偏高/偏低的原因并出图",
            ))
    return items


def detect_temporal(df: pd.DataFrame, profile: DataProfile, z_thresh: float) -> list[AlertItem]:
    """时序突变：每个(指标×维度组)用历史分布做基线，检测最新值是否突变。"""
    items: list[AlertItem] = []
    tc = profile.time_col
    if not tc:
        return items
    d = df.copy()
    d[tc] = pd.to_datetime(d[tc], errors="coerce")
    for metric in profile.metric_cols:
        for label, g in _group_iter(d, profile.dim_cols):
            g = g.dropna(subset=[tc]).sort_values(tc)
            vals = pd.to_numeric(g[metric], errors="coerce").dropna()
            if len(vals) < MIN_TEMPORAL + 1:
                continue
            trail = vals.iloc[:-1]
            med = trail.median()
            mad = (trail - med).abs().median()
            sigma = 1.4826 * mad if (mad and mad > 0) else trail.std()
            if not sigma or sigma <= 0:
                continue
            latest = float(vals.iloc[-1])
            z = (latest - med) / sigma
            if abs(z) > z_thresh:
                items.append(AlertItem(
                    metric=metric,
                    dimension=label,
                    value=latest,
                    expected=float(med),
                    deviation=f"较历史均值偏离 {z:+.1f}σ",
                    level=_level(z),
                    mode=profile.mode,
                    confidence="高" if len(vals) >= 14 else "低",
                    message=f"{label} 的 {metric} 最新为 {latest:,.1f}，显著偏离历史(约{med:,.1f})",
                    drill_question=f"分析{' ' + label if label != '整体' else ''}的 {metric} 近期突变原因并出趋势图",
                ))
    return items


def detect_cross_upload(
    df: pd.DataFrame,
    profile: DataProfile,
    prev: dict,
    drop: float = CROSS_UPLOAD_DROP,
) -> list[AlertItem]:
    """跨次环比：本次各维度聚合 vs 历史快照的同维度聚合，找大跌。"""
    items: list[AlertItem] = []
    prev_agg = prev.get("agg", {})
    if not prev_agg:
        return items
    for metric in profile.metric_cols:
        cur_agg = _aggregate(df, profile, metric)
        for label in set(cur_agg) | set(prev_agg):
            pv = prev_agg.get(label, {}).get(metric)
            cv = cur_agg.get(label)
            if pv is None or cv is None or pv == 0:
                continue
            delta = (cv - pv) / pv
            if delta <= -drop:
                items.append(AlertItem(
                    metric=metric,
                    dimension=label,
                    value=cv,
                    expected=pv,
                    deviation=f"较上次下降 {delta * 100:+.1f}%",
                    level="P1" if delta <= -2 * drop else "P2",
                    mode="cross_upload",
                    confidence="中",
                    message=f"{label} 的 {metric} 本次 {cv:,.1f}，较上次 {pv:,.1f} 下降 {delta * 100:+.1f}%",
                    drill_question=f"分析{' ' + label if label != '整体' else ''}的 {metric} 较上次大幅下降的原因并出图",
                ))
    return items
