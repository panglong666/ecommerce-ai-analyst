"""三套检测器：截面离群 / 时序突变 / 跨次环比。

均使用稳健统计量（中位数 + MAD / 标准差），对小样本与离群点更稳。
每条告警都带 drill_question，供前端一键调分析 Agent 归因。
"""
from __future__ import annotations

import pandas as pd

from ecommerce_ai.alerting.config import (
    CROSS_UPLOAD_DROP,
    FESTIVAL_TOLERANCE_Z,
    FESTIVAL_WINDOWS,
    MIN_GROUP,
    MIN_TEMPORAL,
    MIN_WEEKDAY_SAMPLES,
    RATE_METRICS,
    REFUND_METRIC_HINTS,
    TRAIL_CHANGE_MIN,
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


def festival_note(metric: str, dt) -> str | None:
    """判断某日期是否落在节日窗口内，返回标注文案（否则 None）。

    按指标类型区分窗口：退款/退货类看「节后窗口」（3~N 天集中退货），
    其余（流量/成交/转化）看「节前预热 + 当天」。
    """
    if dt is None:
        return None
    d = dt.date() if hasattr(dt, "date") else dt
    is_refund = any(k in str(metric) for k in REFUND_METRIC_HINTS)
    for name, center, pre, post in FESTIVAL_WINDOWS:
        delta = (d - center).days
        if is_refund:
            if 2 <= delta <= post:
                return f"{name}后 {delta} 天退货窗口"
        elif -pre <= delta <= 0:
            return f"{name}窗口（预热/当天）"
    return None


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
    """时序突变：以「同周几基线」为主（样本不足回退全历史），并叠加环比突变判据。

    为什么同周几：电商有周内节律（周一低、周六高）。用「全历史中位数」作基线时，
    周一/周末的常态波动会被误报为异常（实测：周一低谷被报 -4.0σ）。
    为什么环比判据：z 值 = 偏离 / sigma，波动大的指标（曝光量受总池影响）sigma 大，
    真实断崖也可能落在 3σ 内（实测：商城曝光 -55% 仅 -2.2σ）。环比变化率与离散度无关。
    为什么节日窗口：节前预热（流量涨）与节后退货（退款率涨）属预期波动，需标注并降级。
    """
    items: list[AlertItem] = []
    tc = profile.time_col
    if not tc:
        return items
    d = df.copy()
    d[tc] = pd.to_datetime(d[tc], errors="coerce")

    for metric in profile.metric_cols:
        for label, g in _group_iter(d, profile.dim_cols):
            g = g.dropna(subset=[tc]).sort_values(tc)
            valid = pd.to_numeric(g[metric], errors="coerce").dropna()
            if len(valid) < MIN_TEMPORAL + 1:
                continue

            latest = float(valid.iloc[-1])
            latest_dt = g.loc[valid.index[-1], tc]

            # ① 同周几基线：**中心**取「同周几中位数」以消除周内节律；
            #    **离散度**优先用全历史（样本更充分、估计更稳）——
            #    只用 3 个同周几点算 MAD 会虚高，反而制造误报（单测已抓到）。
            wd = latest_dt.weekday()
            same = valid[[i for i in valid.index if g.loc[i, tc].weekday() == wd]]
            hist = valid.iloc[:-1]
            if len(same) >= MIN_WEEKDAY_SAMPLES:
                center_src, basis = same.iloc[:-1], "同周几"
            else:
                center_src, basis = hist, "全历史"
            if len(center_src) < 2:
                continue
            med = center_src.median()

            sig_src = hist if len(hist) >= 5 else center_src
            mad = (sig_src - sig_src.median()).abs().median()
            sigma = 1.4826 * mad if (mad and mad > 0) else sig_src.std()
            if not sigma or sigma <= 0:
                continue

            z = (latest - med) / sigma

            # ③ 环比突变（二阶检测）：对「变化率」再做一次稳健 z 检验，
            #    与**该指标自身的历史环比分布**比较——既抓得住断崖，
            #    又不会误伤天然波动大的指标（固定阈值 40% 会大面积误报）。
            chg, z_chg = None, 0.0
            prev = float(valid.iloc[-2])
            if prev:
                chg = (latest - prev) / prev
                hist_chg = valid.pct_change().dropna()
                if len(hist_chg) >= 5:
                    mc = hist_chg.median()
                    mdc = (hist_chg - mc).abs().median()
                    sc = 1.4826 * mdc if (mdc and mdc > 0) else hist_chg.std()
                    if sc and sc > 0:
                        z_chg = (chg - mc) / sc

            hit_z = abs(z) > z_thresh                                     # ② 偏离历史水平
            hit_chg = (chg is not None and abs(z_chg) > z_thresh
                       and abs(chg) >= TRAIL_CHANGE_MIN)                  # ③ 环比突变
            if not (hit_z or hit_chg):
                continue

            if hit_z:
                dev = f"较{basis}均值偏离 {z:+.1f}σ"
                lv = _level(z)
                conf = "高" if len(valid) >= 14 else "低"
                if hit_chg:
                    dev += f"（环比 {chg * 100:+.1f}%）"
            else:
                dev = f"环比变化 {chg * 100:+.1f}%（变化率异常度 {z_chg:+.1f}σ）"
                lv = _level(z_chg)
                conf = "中"

            msg = f"{label} 的 {metric} 最新为 {latest:,.1f}，显著偏离历史(约{med:,.1f})"
            # ④ 节日窗口：窗口内「幅度未超预期」→ 降为 P2 提示；「幅度失控」→ 保留原级别。
            #    这样既不误报节后常态退货，也不放过"节后仍异常"的真问题。
            note = festival_note(metric, latest_dt)
            if note:
                z_eff = abs(z) if hit_z else abs(z_chg)
                if z_eff >= FESTIVAL_TOLERANCE_Z:
                    msg += f"（{note}，但幅度显著超出预期）"
                else:
                    lv = "P2"
                    msg += f"（{note}，属预期内波动）"

            items.append(AlertItem(
                metric=metric,
                dimension=label,
                value=latest,
                expected=float(med),
                deviation=dev,
                level=lv,
                mode=profile.mode,
                confidence=conf,
                message=msg,
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
