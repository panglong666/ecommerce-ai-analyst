"""通用预警配置：同义词、时间/ID 列识别、阈值、大促日历。

集中在此便于业务方按自己行业调整，无需改算法代码。
"""
from __future__ import annotations

# 时间列名关键词（不区分大小写）
TIME_COL_HINTS = [
    "date", "time", "日期", "时间", "天", "day",
    "月份", "month", "周", "week", "datetime",
]

# ID 列排除关键词（高基数、疑似主键，不应作为指标）
ID_COL_HINTS = ["id", "编号", "编码", "序号", "index", "主键", "key", "sku_id", "订单号"]

# 指标列同义词 -> 规范名（用于展示与跨表对齐）
METRIC_SYNONYMS = {
    "sales": ["销售额", "成交金额", "成交总额", "gmv", "gmw", "流水", "营收", "销售金额", "amount", "sales"],
    "orders": ["订单量", "订单数", "下单量", "成交量", "orders", "order_cnt"],
    "refund": ["退款率", "退货率", "退款", "退货", "refund", "return_rate"],
    "views": ["浏览量", "曝光量", "访问量", "pv", "views", "impressions", "曝光"],
    "clicks": ["点击量", "点击数", "clicks", "click", "点击"],
    "cart": ["加购数", "加购量", "购物车", "cart", "add_cart", "加购"],
    "price": ["价格", "单价", "客单价", "price", "avg_price", "均价"],
    "stock": ["库存", "库存量", "stock", "inventory", "现货"],
}
# 由同义词反查规范名（小写匹配）
_SYN_TO_CANON = {s.lower(): c for c, syns in METRIC_SYNONYMS.items() for s in syns}

# 比率型指标（跨次对比用均值而非求和，避免重复累加失真）
RATE_METRICS = {"refund"}

# 大促 / 节假日日历（月, 日）—这些日期的异常标注“预期内”，不升级
PROMO_DATES = {
    (11, 11), (6, 18), (12, 12), (1, 1), (5, 1), (10, 1),
    (2, 14), (3, 8), (8, 18), (3, 15), (11, 1),
}

# 最小样本量
MIN_GROUP = 5          # 截面分组至少行数
MIN_TEMPORAL = 7       # 时序基线至少天数（含最新值则需 >=8 个点）

# 灵敏度 -> z 阈值（越大越保守，误报少但可能漏报）
SENSITIVITY_Z = {"conservative": 4.0, "standard": 3.0, "sensitive": 2.0}

# 跨次环比大跌阈值（相对变化）
CROSS_UPLOAD_DROP = 0.30


def canonical_metric(col_name: str) -> str:
    """把任意指标列名映射到规范名（找不到则返回原名）。"""
    return _SYN_TO_CANON.get(str(col_name).strip().lower(), col_name)
