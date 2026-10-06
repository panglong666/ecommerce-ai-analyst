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


def test_high_cardinality_metrics_not_excluded():
    """防回归：高基数的连续指标不应被当成 ID 排除。

    早期判据 `nunique > max(50, 0.9*行数)` 在真实报表上（行数多 + 指标基数天然高）
    会把曝光量、成交金额、未取整的转化率**几乎全部误杀**，导致预警静默失效。
    小样本单测（阈值恰为 50）无法暴露，这里用 200 行构造真实量级。
    """
    n = 200
    rng = np.random.default_rng(7)
    df = pd.DataFrame({
        "日期": _dates(n),
        "渠道": (["直播", "短视频", "商城", "搜索"] * (n // 4)),
        "曝光量(次)": rng.integers(10000, 60000, n),          # 高基数整数（非连续）
        "成交金额(元)": rng.uniform(1000, 90000, n).round(2),  # 高基数浮点
        "支付转化率(%)": rng.uniform(0.01, 0.08, n),           # 未取整 → 基数 = n
    })
    p = profile_table(df)
    for col in ["曝光量(次)", "成交金额(元)", "支付转化率(%)"]:
        assert col in p.metric_cols, f"{col} 不应被当作 ID 排除"
    assert "渠道" in p.dim_cols


def test_pure_sequence_col_excluded():
    """整数且完美连续的序号列（1,2,3,…）应被排除，其余数值列保留。"""
    df = pd.DataFrame({
        "序号": list(range(1, 31)),
        "销售额": np.random.default_rng(8).uniform(100, 200, 30),
    })
    p = profile_table(df)
    assert "序号" not in p.metric_cols
    assert "销售额" in p.metric_cols
