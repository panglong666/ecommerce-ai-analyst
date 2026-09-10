"""数据管理路由：上传结构化数据、数据集列表、删除。"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File
from sqlalchemy import inspect, text

from ecommerce_ai.core.errors import FRIENDLY_400, safe_http
from ecommerce_ai.data.ingest import ingest_structured_file, save_upload
from ecommerce_ai.data.source import get_data_source

router = APIRouter(prefix="/api/v1")


@router.post("/data/upload")
async def upload_data(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    path = save_upload(content, file.filename or "upload.csv")
    try:
        info = ingest_structured_file(path)
    except Exception as e:  # noqa: BLE001
        raise safe_http(400, FRIENDLY_400, e, "upload")
    return {"success": True, "dataset": info.model_dump()}


@router.get("/datasets")
def datasets() -> list[dict]:
    return [d.model_dump() for d in get_data_source().datasets()]


@router.delete("/datasets/{name}")
def delete_dataset(name: str) -> dict:
    src = get_data_source()
    engine = getattr(src, "engine", None)
    if engine is None:
        raise safe_http(400, "当前数据源不支持删除", context="delete")
    # 白名单校验：只允许删除真实存在的表，杜绝表名注入
    tables = inspect(engine).get_table_names()
    if name not in tables:
        raise safe_http(404, "未找到该数据集", context="delete")
    with engine.connect() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
        conn.commit()
    return {"success": True, "deleted": name}
