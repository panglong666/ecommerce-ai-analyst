"""异常预警 Agent：扫描核心指标，发现异常并归因。"""
from __future__ import annotations

from ecommerce_ai.data.source import get_data_source


def scan_alerts() -> dict:
    """扫描退款率、GMV 等指标，返回异常清单与归因。"""
    src = get_data_source()
    tables = src.list_tables()

    anomalies: list[dict] = []
    attribution: list[str] = []

    if "daily_metrics" in tables:
        res = src.query(
            "SELECT region, ROUND(AVG(refund_rate),4) AS avg_refund, "
            "ROUND(SUM(gmv),2) AS total_gmv FROM daily_metrics GROUP BY region "
            "ORDER BY avg_refund DESC"
        )
        for r in res.rows:
            if (r.get("avg_refund") or 0) > 0.08:
                anomalies.append({
                    "region": r["region"],
                    "metric": "refund_rate",
                    "value": r["avg_refund"],
                    "level": "高" if r["avg_refund"] > 0.12 else "中",
                })
                attribution.append(f"{r['region']} 退款率 {r['avg_refund']:.2%} 偏高，建议核查尺码描述与发货时效。")

        # GMV 同比环比异常（简化：找 GMV 最低区域）
        res2 = src.query(
            "SELECT region, ROUND(SUM(gmv),2) AS total_gmv FROM daily_metrics GROUP BY region "
            "ORDER BY total_gmv ASC LIMIT 1"
        )
        if res2.rows:
            low = res2.rows[0]
            attribution.append(f"{low['region']} GMV 区域排名最低（¥{low['total_gmv']:.0f}），建议加大该区域投放。")
    else:
        attribution.append("未找到 daily_metrics 表，请先运行 sample_data 造数。")

    return {
        "scanned_regions": len(anomalies),
        "anomalies": anomalies,
        "attribution": attribution,
        "advice": "建议优先处理退款率偏高区域的商品详情与物流；对低 GMV 区域增加营销资源。" if anomalies else "暂未发现明显异常。",
    }
