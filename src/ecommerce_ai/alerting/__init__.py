"""通用自适应预警包。

核心思路：上传任意结构的数据表后，先 `profile_table` 自动识别
时间列 / 指标列 / 维度列并选定监测模式，再按模式调用对应的检测器
（截面离群 / 时序突变 / 跨次环比），最后分级并给出可下钻归因的问题。
"""
from ecommerce_ai.alerting.profiler import profile_table
from ecommerce_ai.alerting.rules import (
    detect_cross_section,
    detect_cross_upload,
    detect_temporal,
)
from ecommerce_ai.alerting.snapshots import get_previous, store_snapshot

__all__ = [
    "profile_table",
    "detect_cross_section",
    "detect_temporal",
    "detect_cross_upload",
    "store_snapshot",
    "get_previous",
]
