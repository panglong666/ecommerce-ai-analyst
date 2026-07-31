"""知识库路由：检索、上传文档、重建索引。"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from ecommerce_ai.data.ingest import save_upload
from ecommerce_ai.rag.indexer import index_default_docs, index_file
from ecommerce_ai.tools.rag_tool import search_knowledge

router = APIRouter(prefix="/api/v1")


@router.get("/knowledge/search")
def search(q: str, top_k: int = 5) -> dict:
    return {"query": q, "results": search_knowledge(q, top_k)}


@router.post("/knowledge/upload")
async def upload_doc(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    path = save_upload(content, file.filename or "doc.txt")
    info = index_file(path, source_name=file.filename)
    return {"success": True, "source": info["source"], "chunks": info["chunks"]}


@router.post("/knowledge/reindex")
def reindex() -> dict:
    n = index_default_docs()
    return {"indexed_docs": n}
