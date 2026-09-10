"""数据画像单元测试：覆盖四种数据形态 → 模式选择。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ecommerce_ai.alerting.profiler import profile_table


def _dates(n, start="2026-01-01"):
    return pd.date_range(start, periods=n, freq="D").strftime("%Y-%m-%d")


def test_single_day_cross_section():
    # 单日快照：无时间跨度 → 截面对比
    df = pd.DataFrame({
        "品类": ["连衣裙", "T恤", "裤子"] * 3,
        "销售额": [100, 120, 90, 110, 130, 95, 105, 125, 88],
    })
    p = profile_table(df)
    assert p.mode == "cross_section"
    assert "销售额" in p.metric_cols
    assert "品类" in p.dim_cols
    assert p.time_col is None


def test_multi_day_temporal():
    # 30 天时序 → 标准时序
    df = pd.DataFrame({
        "日期": _dates(30),
        "销售额": np.random.default_rng(0).uniform(100, 200, 30),
    })
    p = profile_table(df)
    assert p.mode == "temporal"
    assert p.time_col == "日期"
    assert "销售额" in p.metric_cols
    assert p.time_range_days == 29


def test_multi_year_full_temporal():
    # 跨年 → 完整时序
    dates = pd.date_range("2024-01-01", "2026-03-01", freq="D")
    df = pd.DataFrame({
        "日期": dates.strftime("%Y-%m-%d"),
        "销售额": np.random.default_rng(1).uniform(100, 200, len(dates)),
    })
    p = profile_table(df)
    assert p.mode == "full_temporal"


def test_no_time_col_cross_section():
    # 有数值列但无时间列 → 截面对比
    df = pd.DataFrame({
        "区域": ["华东", "华北", "华南"] * 4,
        "GMV": [1000, 1200, 900, 1100, 1300, 950, 1050, 1250, 880, 1150, 1350, 920],
    })
    p = profile_table(df)
    assert p.mode == "cross_section"
    assert "GMV" in p.metric_cols


def test_weak_temporal_short_span():
    # 10 天 → 弱时序(低置信)
    df = pd.DataFrame({
        "日期": _dates(10),
        "销售额": np.random.default_rng(2).uniform(100, 200, 10),
    })
    p = profile_table(df)
    assert p.mode == "weak_temporal"
