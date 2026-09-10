"""对话路由：POST /api/v1/chat（流式 SSE）。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ecommerce_ai.agents.graph import stream_run
from ecommerce_ai.api.schemas import ChatRequest

logger = logging.getLogger("ecommerce_ai.api.chat")

router = APIRouter(prefix="/api/v1")


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """流式对话：以 SSE（text/event-stream）逐节点推送结果。

    事件格式：`data: {json}\\n\\n`，json 含 type 字段（route/sql/rows/chart/answer/done/error）。
    内部异常只记日志，对外发友好 error 事件，绝不回显堆栈。
    """

    async def event_gen():
        try:
            async for ev in stream_run(req.question, dataset=req.dataset, mode=req.mode):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            logger.exception("chat stream failed: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': '服务内部错误，请稍后重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
