"""检测器单元测试：截面离群 / 时序突变 / 跨次环比。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ecommerce_ai.alerting.profiler import profile_table
from ecommerce_ai.alerting.rules import (
    detect_cross_section,
    detect_cross_upload,
    detect_temporal,
)
from ecommerce_ai.alerting.config import SENSITIVITY_Z


def test_cross_section_finds_outlier():
    # 某品类销售额远高于同组 → 应检出
    df = pd.DataFrame({
        "品类": ["连衣裙"] * 8 + ["T恤"] * 8,
        "销售额": [100, 105, 98, 102, 99, 101, 97, 103, 5000, 95, 98, 102, 99, 101, 97, 103],
    })
    p = profile_table(df)
    items = detect_cross_section(df, p, SENSITIVITY_Z["standard"])
    assert any(it.dimension == "T恤" and "销售额" in it.metric for it in items)


def test_temporal_finds_spike():
    # 最后一天突变暴涨 → 应检出
    rng = np.random.default_rng(3)
    base = rng.uniform(100, 150, 20)
    vals = np.concatenate([base, [1000.0]])  # 第21天暴涨
    df = pd.DataFrame({
        "日期": pd.date_range("2026-01-01", periods=21, freq="D").strftime("%Y-%m-%d"),
        "销售额": vals,
    })
    p = profile_table(df)
    items = detect_temporal(df, p, SENSITIVITY_Z["standard"])
    assert any("销售额" in it.metric for it in items)


def test_temporal_no_false_positive_on_stable():
    # 平稳序列 → 不应误报
    rng = np.random.default_rng(4)
    vals = rng.uniform(100, 110, 25)
    df = pd.DataFrame({
        "日期": pd.date_range("2026-01-01", periods=25, freq="D").strftime("%Y-%m-%d"),
        "销售额": vals,
    })
    p = profile_table(df)
    items = detect_temporal(df, p, SENSITIVITY_Z["standard"])
    assert items == []


def test_cross_upload_finds_drop():
    # 本次某维度较上次大幅下降 → 应检出（需上一快照 agg）
    df = pd.DataFrame({
        "品类": ["连衣裙", "T恤"],
        "销售额": [100, 80],
    })
    p = profile_table(df)
    prev = {"name": "t", "ts": "x", "agg": {"连衣裙": {"销售额": 200}, "T恤": {"销售额": 160}}}
    items = detect_cross_upload(df, p, prev)
    assert any(it.dimension == "连衣裙" and "销售额" in it.metric for it in items)
    assert all("下降" in it.deviation for it in items)
