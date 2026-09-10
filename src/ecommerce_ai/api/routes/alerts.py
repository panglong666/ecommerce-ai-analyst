"""预警路由。

- POST /api/v1/alerts/scan  扫描异常（自适应）
- GET  /api/v1/alerts/profile 返回某数据集的画像与监测模式（前端据此展示徽标/控件）
"""
from __future__ import annotations

from fastapi import APIRouter

from ecommerce_ai.alerting.profiler import profile_table
from ecommerce_ai.agents.nodes.alert import scan_alerts
from ecommerce_ai.api.schemas import AlertScanRequest
from ecommerce_ai.core.models import AlertScanResponse
from ecommerce_ai.data.source import get_data_source

router = APIRouter(prefix="/api/v1")

_MONITORING = {
    "cross_section": "截面对比",
    "weak_temporal": "弱时序(低置信)",
    "temporal": "标准时序",
    "full_temporal": "完整时序(含同比/季节)",
}


@router.post("/alerts/scan")
def scan(req: AlertScanRequest) -> AlertScanResponse:
    return scan_alerts(req)


@router.get("/alerts/profile")
def profile(dataset: str = "") -> dict:
    src = get_data_source()
    tables = src.list_tables()
    target = dataset or next((t for t in tables if t.lower() != "alert_snapshots"), None)
    if not target:
        return {"ok": False, "message": "无可用数据集"}
    try:
        df = src.read_table(target)
        prof = profile_table(df)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"读取失败: {e}"}
    return {
        "ok": True,
        "dataset": target,
        "profile": prof.model_dump(),
        "monitoring": _MONITORING.get(prof.mode, prof.mode),
        "metrics": prof.metric_cols,
        "time_col": prof.time_col,
        "dim_cols": prof.dim_cols,
    }
