"""通用自适应预警编排：画像 → 选模式 → 调检测器 → 分级 → 归因入口。

替换原写死的 scan_alerts（只盯 daily_metrics）。
"""
from __future__ import annotations

import pandas as pd

from ecommerce_ai.alerting.config import PROMO_DATES, SENSITIVITY_Z
from ecommerce_ai.alerting.profiler import profile_table
from ecommerce_ai.alerting.rules import (
    detect_cross_section,
    detect_cross_upload,
    detect_temporal,
)
from ecommerce_ai.alerting.snapshots import get_previous
from ecommerce_ai.api.schemas import AlertScanRequest
from ecommerce_ai.core.models import AlertScanResponse
from ecommerce_ai.data.source import get_data_source

_MONITORING_LABEL = {
    "cross_section": "截面对比",
    "weak_temporal": "弱时序(低置信)",
    "temporal": "标准时序",
    "full_temporal": "完整时序(含同比/季节)",
    "cross_upload": "跨次环比",
}
_LEVEL_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def _pick_table(tables: list[str], dataset: str) -> str | None:
    if dataset:
        return dataset if dataset in tables else None
    for t in tables:
        if t.lower() != "alert_snapshots":
            return t
    return None


def scan_alerts(req: AlertScanRequest | None = None) -> AlertScanResponse:
    req = req or AlertScanRequest()
    src = get_data_source()
    tables = src.list_tables()
    target = _pick_table(tables, req.dataset)
    if not target:
        return AlertScanResponse(notes=["无可用数据集"], advice="请先上传结构化数据。")

    try:
        df = src.read_table(target)
    except Exception as e:  # noqa: BLE001
        return AlertScanResponse(dataset=target, notes=[f"读取表失败: {e}"], advice="数据读取异常。")
    if df is None or df.empty:
        return AlertScanResponse(dataset=target, notes=["表为空"], advice="请上传含数据的文件。")

    profile = profile_table(df, req.time_col, req.metric_cols, req.dim_cols)
    z = SENSITIVITY_Z.get(req.sensitivity, 3.0)

    items = []
    if profile.mode in ("weak_temporal", "temporal", "full_temporal"):
        items += detect_temporal(df, profile, z)
    else:
        items += detect_cross_section(df, profile, z)

    prev = get_previous(target)
    if prev:
        items += detect_cross_upload(df, profile, prev)

    items = _apply_seasonal(items, df, profile)
    items.sort(key=lambda x: _LEVEL_ORDER.get(x.level, 9))

    advice = "未发现明显异常。" if not items else (
        f"共 {len(items)} 条告警，建议优先处理 P0/P1；"
        "点击「深入归因」调用分析 Agent 查看原因与图表。"
    )
    return AlertScanResponse(
        dataset=target,
        mode=profile.mode,
        monitoring=_MONITORING_LABEL.get(profile.mode, profile.mode),
        notes=profile.notes,
        anomalies=items[:30],
        advice=advice,
        scanned=len(items),
    )


def _apply_seasonal(items, df: pd.DataFrame, profile) -> list:
    """完整时序下，最新值命中大促/节假日日历则降级并标注预期内。"""
    if profile.mode != "full_temporal" or not profile.time_col:
        return items
    ts = pd.to_datetime(df[profile.time_col], errors="coerce").dropna()
    if ts.empty:
        return items
    if (ts.max().month, ts.max().day) in PROMO_DATES:
        for it in items:
            it.message += "（最新值处于大促/节假日，可能为预期内波动）"
            if it.level == "P0":
                it.level = "P1"
    return items
