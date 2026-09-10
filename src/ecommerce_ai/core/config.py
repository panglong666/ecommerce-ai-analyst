"""全局配置：pydantic-settings 读取 .env，覆盖默认值。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/ecommerce_ai/core/config.py -> 上溯 3 层到项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ===== 大模型 =====
    llm_provider: str = "deepseek"  # deepseek / mock
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # ===== 嵌入 =====
    embedding_provider: str = "chroma_default"  # chroma_default / local_bge
    bge_model: str = "BAAI/bge-small-zh-v1.5"

    # ===== 数据源 =====
    data_source: str = "mock"  # mock / warehouse
    sqlite_path: str = "data/mock.sqlite"
    upload_dir: str = "data/uploads"
    docs_subdir: str = "docs"  # 知识库策划语料子目录；reindex / 种子 / 上传共用，可在 .env 配置

    # ===== 向量库 =====
    vector_store: str = "chroma"
    chroma_path: str = "data/chroma"

    # ===== 服务 =====
    host: str = "127.0.0.1"
    port: int = 8000

    # ===== 安全 =====
    # 可选 API Key：留空=演示模式免鉴权；非空时所有 API 需带 X-API-Key 头
    api_key: str = ""
    # CORS 白名单（逗号分隔）。默认仅本机前端；公网部署请改为前端真实域名
    cors_origins: str = "http://127.0.0.1:8000"

    # ===== 检索 =====
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ===== 可观测 =====
    langsmith_tracing: bool = False

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的 cors_origins 转成列表，供 CORS 中间件使用。"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def abs(self, relative: str) -> Path:
        """把相对路径转成相对项目根的绝对路径。"""
        return PROJECT_ROOT / relative

    def ensure_dirs(self) -> None:
        (PROJECT_ROOT / self.upload_dir).mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / self.chroma_path).mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()
