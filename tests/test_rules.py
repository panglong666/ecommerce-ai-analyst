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


def test_snapshot_roundtrip_is_consumable():
    """防回归：store_snapshot 写入的结构必须能被 detect_cross_upload 正确消费。

    覆盖两个曾经的静默 bug：
    1) 写入键序写成 {指标: {维度}}，而检测器期望 {维度: {指标}}；
    2) get_previous 用 rows[-2] 在 len==2 时取到「本次」而非「上一次」，
       导致自己跟自己比 → 永远 0 差异、且不报错。
    """
    from sqlalchemy import text

    from ecommerce_ai.alerting.snapshots import _SNAP_TABLE, get_previous, store_snapshot
    from ecommerce_ai.data.source import get_data_source

    name = "__pytest_roundtrip__"
    src = get_data_source()
    with src.engine.connect() as conn:
        conn.execute(text(f"DELETE FROM {_SNAP_TABLE} WHERE name=:n"), {"n": name})
        conn.commit()

    n = 12
    v1 = pd.DataFrame({"品类": (["A", "B"] * n), "销售额": [100.0] * (2 * n)})
    v2 = pd.DataFrame({"品类": (["A", "B"] * n), "销售额": ([100.0, 20.0] * n)})

    store_snapshot(name, v1)
    store_snapshot(name, v2)

    prev = get_previous(name)
    assert prev is not None, "应能取到上一次快照"
    # 结构必须是 {维度: {指标: 值}}（否则检测器取不到）
    assert "A" in prev["agg"] and "销售额" in prev["agg"]["A"]

    items = detect_cross_upload(v2, profile_table(v2), prev)
    assert items, "B 组销售额 100→20（-80%）应被跨次环比检出"
