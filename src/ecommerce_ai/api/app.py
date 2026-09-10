"""FastAPI 应用入口。"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ecommerce_ai.api.routes import alerts, chat, data, knowledge, query
from ecommerce_ai.core.config import settings

app = FastAPI(title="电商数据分析 AI 应用", version="0.1.0")

# CORS 白名单：默认仅本机前端；公网部署请在 .env 设置 cors_origins 为前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """可选 API Key 校验：仅当配置了 api_key 才启用，否则演示模式放行。"""
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="未授权：缺少或错误的 API Key")


# 所有 API 路由统一加上鉴权依赖（api_key 留空时该依赖为 no-op）
_api_deps = [Depends(verify_api_key)]
app.include_router(chat.router, dependencies=_api_deps)
app.include_router(query.router, dependencies=_api_deps)
app.include_router(knowledge.router, dependencies=_api_deps)
app.include_router(data.router, dependencies=_api_deps)
app.include_router(alerts.router, dependencies=_api_deps)


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_source": settings.data_source,
        "llm_provider": settings.llm_provider,
        "llm_configured": bool(settings.deepseek_api_key),
    }


# 前端单页（必须在 API 路由之后挂载，避免吞掉 /api/v1/*）
_frontend_dir = settings.project_root / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
