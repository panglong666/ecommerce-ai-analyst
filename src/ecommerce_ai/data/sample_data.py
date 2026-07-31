"""造数脚本：生成示例订单/商品/指标表到 SQLite，并写入示例知识文档。

运行：python -m ecommerce_ai.data.sample_data
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import pandas as pd

from ecommerce_ai.core.config import settings
from ecommerce_ai.data.mock_source import MockSource

CATEGORIES = ["羽绒服", "连衣裙", "面膜", "手机", "耳机", "运动鞋", "休闲零食", "家用电器"]
REGIONS = ["华东", "华北", "华南", "华中", "西南", "西北", "东北"]
CHANNELS = ["天猫", "京东", "抖音", "拼多多", "自营"]
BRANDS = ["A牌", "B牌", "C牌", "D牌", "E牌"]


def _products() -> pd.DataFrame:
    rows = []
    for i, cat in enumerate(CATEGORIES):
        for b in BRANDS:
            sku = f"SKU{cat}{b}".replace("牌", "")
            rows.append({
                "sku": sku,
                "name": f"{b}{cat}{random.randint(100, 999)}",
                "category": cat,
                "brand": b,
                "price": round(random.uniform(39, 2999), 2),
            })
    return pd.DataFrame(rows)


def _orders(products: pd.DataFrame) -> pd.DataFrame:
    rows = []
    start = date(2024, 1, 1)
    days = 365
    pid = products["sku"].tolist()
    for d in range(days):
        day = start + timedelta(days=d)
        n = random.randint(6, 14)  # 每天订单数
        for _ in range(n):
            sku = random.choice(pid)
            prod = products[products["sku"] == sku].iloc[0]
            qty = random.randint(1, 5)
            amount = round(float(prod["price"]) * qty, 2)
            rows.append({
                "order_id": f"O{d:04d}{random.randint(1000,9999)}",
                "sku": sku,
                "category": prod["category"],
                "region": random.choice(REGIONS),
                "channel": random.choice(CHANNELS),
                "order_date": day.isoformat(),
                "quantity": qty,
                "amount": amount,
                "refund": round(amount * random.choice([0, 0, 0, 0, 0.1]), 2),
            })
    # 给冬季类目（羽绒服）在 11/12 月加量
    df = pd.DataFrame(rows)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.month
    winter_extra = df[(df["category"] == "羽绒服") & (df["month"].isin([11, 12]))]
    df = pd.concat([df, winter_extra, winter_extra], ignore_index=True)
    df = df.drop(columns=["month"])
    return df


def _daily_metrics(orders: pd.DataFrame) -> pd.DataFrame:
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["date"] = orders["order_date"].dt.date
    g = orders.groupby(["date", "region"]).agg(
        gmv=("amount", "sum"),
        refund=("refund", "sum"),
        orders_n=("order_id", "count"),
    ).reset_index()
    g["refund_rate"] = (g["refund"] / g["gmv"]).round(4)
    g = g.rename(columns={"date": "metric_date"})
    return g[["metric_date", "region", "gmv", "refund_rate", "orders_n"]]


DOCS = {
    "羽绒服运营手册.txt": (
        "【羽绒服类目运营手册】\n"
        "1. 羽绒服为强季节品类，9月起预热，10-12月为爆发期，次年1月清仓。\n"
        "2. 华东、华北为主力销售区域，西北、东北需求集中但物流时效要求高。\n"
        "3. 定价带：基础款 199-499，轻奢款 699-1299。\n"
        "4. 退货率控制目标 < 12%，主要退货原因为尺码不合与绒量不符。\n"
    ),
    "售后政策.txt": (
        "【售后政策】\n"
        "1. 七天无理由退货：商品签收次日起 7 天内，商品完好可申请无理由退货。\n"
        "2. 质量问题：30 天内可申请退换，运费由平台承担。\n"
        "3. 羽绒服类目因季节性强，3 月 1 日起停止七天无理由退货服务。\n"
        "4. 退款到账时效：原路退回 1-3 个工作日。\n"
    ),
    "华东区Q4复盘.txt": (
        "【华东区 Q4 复盘】\n"
        "Q4 华东区 GMV 同比增长 18%，主要由羽绒服与家用电器驱动。\n"
        "羽绒服同比 +23.5%，高于大盘 +12%；抖音渠道增速最快。\n"
        "风险点：12 月退款率环比上升 1.2pct，需关注尺码描述准确性。\n"
    ),
}


def write_docs() -> list[str]:
    docs_dir = settings.abs(settings.upload_dir) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, content in DOCS.items():
        p = docs_dir / name
        p.write_text(content, encoding="utf-8")
        paths.append(str(p))
    return paths


def main() -> None:
    random.seed(42)
    src = MockSource()
    print("[sample_data] 生成商品表...")
    products = _products()
    products.to_sql("products", src.engine, if_exists="replace", index=False)

    print("[sample_data] 生成订单表...")
    orders = _orders(products)
    orders.to_sql("orders", src.engine, if_exists="replace", index=False)

    print("[sample_data] 生成日粒度指标表...")
    metrics = _daily_metrics(orders)
    metrics.to_sql("daily_metrics", src.engine, if_exists="replace", index=False)

    print(f"[sample_data] 写入示例文档 {len(write_docs())} 篇到 data/uploads/docs/")

    print("\n造数完成：")
    print(f"  products        {len(products)} 行")
    print(f"  orders          {len(orders)} 行")
    print(f"  daily_metrics   {len(metrics)} 行")
    print(f"  SQLite: {src.path}")


if __name__ == "__main__":
    main()
