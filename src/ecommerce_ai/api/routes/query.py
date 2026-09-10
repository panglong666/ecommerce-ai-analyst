"""单轮分析路由：POST /api/v1/query。"""
from __future__ import annotations

from fastapi import APIRouter

from ecommerce_ai.agents.graph import run
from ecommerce_ai.api.schemas import ChatRequest
from ecommerce_ai.core.errors import FRIENDLY_500, safe_http
from ecommerce_ai.core.models import AgentResponse

router = APIRouter(prefix="/api/v1")


@router.post("/query", response_model=AgentResponse)
def query(req: ChatRequest) -> AgentResponse:
    try:
        return run(req.question, dataset=req.dataset, mode=req.mode)
    except Exception as e:  # noqa: BLE001
        raise safe_http(500, FRIENDLY_500, e, "query")
