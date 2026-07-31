"""预警路由：POST /api/v1/alerts/scan。"""
from __future__ import annotations

from fastapi import APIRouter

from ecommerce_ai.agents.nodes.alert import scan_alerts

router = APIRouter(prefix="/api/v1")


@router.post("/alerts/scan")
def scan() -> dict:
    return scan_alerts()
