"""知识库路由：检索、上传文档、重建索引。"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from ecommerce_ai.core.config import settings
from ecommerce_ai.data.ingest import save_upload
from ecommerce_ai.rag.indexer import index_default_docs, index_file
from ecommerce_ai.tools.rag_tool import search_knowledge

router = APIRouter(prefix="/api/v1")


@router.get("/knowledge/search")
def search(q: str, top_k: int = 5, domain: str = "") -> dict:
    """知识库检索。domain 为空=全库；bandao=半岛产品；apparel=电商示例。"""
    return {"query": q, "domain": domain, "results": search_knowledge(q, top_k, domain=domain)}


@router.post("/knowledge/upload")
async def upload_doc(file: UploadFile = File(...), domain: str = "") -> dict:
    """上传并索引文档。domain 留空时按文件名自动推断（含「半岛」→ bandao）。"""
    content = await file.read()
    path = save_upload(content, file.filename or "doc.txt", subdir=settings.docs_subdir)
    info = index_file(path, source_name=file.filename, domain=domain or None)
    return {"success": True, "source": info["source"], "chunks": info["chunks"], "domain": info["domain"]}


@router.post("/knowledge/reindex")
def reindex(domain: str = "") -> dict:
    """按 docs 目录重建索引。domain 留空时每个文档按文件名自动推断归属。"""
    n = index_default_docs(domain=domain or None)
    return {"indexed_docs": n}
