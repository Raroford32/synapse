"""Document management endpoints"""
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends
from pydantic import BaseModel
from fastapi import Request
from app.core.services import ServiceManager

from app.core.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    use_memory: bool = True


@router.post("/documents/upload")
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(None)
):
    """Upload documents to the RAG system"""
    services: ServiceManager = request.app.state.services
    uploaded = []
    for file in files:
        content = await file.read()
        doc = await services.rag.ingest_bytes(file.filename, content)
        uploaded.append({"filename": file.filename, "size": len(content), "status": "indexed", "id": doc["id"]})
    
    return {
        "status": "success",
        "documents": uploaded,
        "count": len(uploaded)
    }


@router.post("/documents/search")
async def search_documents(
    request: SearchRequest,
    req: Request,
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """Search documents with optional memory context"""
    services: ServiceManager = req.app.state.services
    results = await services.rag.search(request.query, limit=request.limit)
    return {
        "query": request.query,
        "results": results,
        "count": len(results),
        "user_context_applied": request.use_memory and x_user_id is not None,
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Delete a document from the system"""
    services: ServiceManager = request.app.state.services
    ok = await services.rag.delete(document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "document_id": document_id}