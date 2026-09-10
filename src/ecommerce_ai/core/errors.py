"""统一错误处理：服务端记录原始异常，对外只返回友好文案 + 正确状态码。

设计原则：
- 内部异常的细节（路径 / SQL / 第三方报错）只记日志，绝不回显给前端。
- 对外一律用中文友好文案，并配合 4xx/5xx 状态码（而非恒 200）。
"""
from __future__ import annotations

import logging

from fastapi import HTTPException

logger = logging.getLogger("ecommerce_ai.errors")

FRIENDLY_400 = "请求无法处理，请检查输入后重试"
FRIENDLY_404 = "请求的资源不存在"
FRIENDLY_500 = "服务内部错误，请稍后重试"


def log_error(exc: Exception, context: str = "") -> None:
    """记录原始异常（含堆栈），供排查；不向用户暴露。"""
    tag = f" ({context})" if context else ""
    logger.exception("未处理异常%s: %s", tag, exc)


def safe_http(
    status_code: int,
    friendly: str = FRIENDLY_500,
    exc: Exception | None = None,
    context: str = "",
) -> HTTPException:
    """构造一个对外友好的 HTTPException，并在内部记录原始异常。"""
    if exc is not None:
        log_error(exc, context)
    return HTTPException(status_code=status_code, detail=friendly)
