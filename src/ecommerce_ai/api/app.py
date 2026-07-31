"""FastAPI 应用入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ecommerce_ai.api.routes import alerts, chat, data, knowledge, query
from ecommerce_ai.core.config import settings

app = FastAPI(title="电商数据分析 AI 应用", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_source": settings.data_source,
        "llm_provider": settings.llm_provider,
        "llm_configured": bool(settings.deepseek_api_key),
    }


app.include_router(chat.router)
app.include_router(query.router)
app.include_router(knowledge.router)
app.include_router(data.router)
app.include_router(alerts.router)

# 前端单页（必须在 API 路由之后挂载，避免吞掉 /api/v1/*）
_frontend_dir = settings.project_root / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
