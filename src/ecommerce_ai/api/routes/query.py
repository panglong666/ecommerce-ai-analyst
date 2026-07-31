"""单轮分析路由：POST /api/v1/query。"""
from __future__ import annotations

from fastapi import APIRouter

from ecommerce_ai.agents.graph import run
from ecommerce_ai.api.schemas import ChatRequest
from ecommerce_ai.core.models import AgentResponse

router = APIRouter(prefix="/api/v1")


@router.post("/query", response_model=AgentResponse)
def query(req: ChatRequest) -> AgentResponse:
    try:
        return run(req.question)
    except Exception as e:  # noqa: BLE001
        return AgentResponse(question=req.question, answer=f"处理失败：{e}", route="error")
