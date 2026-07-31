"""外部 API 工具（占位）。

接入示例：物流轨迹、广告投放、舆情等。用 httpx 封装，统一鉴权限流。
此处提供桩函数，便于 Agent 调用与后续替换。
"""
from __future__ import annotations


def query_logistics(order_id: str) -> dict:
    """查询物流轨迹（占位）。"""
    return {"order_id": order_id, "status": "在途", "eta": "2 天内", "note": "占位数据，接入真实物流 API 后替换"}


def query_ad_roi(campaign: str) -> dict:
    """查询广告投放 ROI（占位）。"""
    return {"campaign": campaign, "spend": 0.0, "roi": 0.0, "note": "占位数据，接入广告平台 API 后替换"}
