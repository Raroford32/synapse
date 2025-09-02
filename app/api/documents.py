"""Document management and RAG endpoints"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    user_id: str = Form(default="default"),
    collection_name: Optional[str] = Form(None),
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Ingest documents for RAG"""
    
    services = req.app.state.services
    
    if not services.rag:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    results = []
    errors = []
    
    # Create collection if specified
    collection = None
    if collection_name:
        try:
            collection = await services.rag.create_collection(
                db, user_id, collection_name
            )
        except Exception as e:
            logger.warning(f"Failed to create collection: {e}")
    
    for file in files:
        try:
            # Check file size
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                errors.append({
                    "filename": file.filename,
                    "error": f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)"
                })
                continue
            
            # Check file extension
            import os
            ext = os.path.splitext(file.filename)[1].lower()
            allowed_exts = [f".{e}" for e in settings.ALLOWED_FILE_EXTENSIONS.split(",")]
            
            if ext not in allowed_exts:
                errors.append({
                    "filename": file.filename,
                    "error": f"File type {ext} not allowed"
                })
                continue
            
            # Ingest document
            document = await services.rag.ingest_document(
                db,
                user_id,
                file.filename,
                content,
                file.filename,
                metadata={"content_type": file.content_type}
            )
            
            # Add to collection if specified
            if collection:
                await services.rag.add_to_collection(
                    db, str(document.id), str(collection.id), user_id
                )
            
            results.append({
                "id": str(document.id),
                "filename": document.filename,
                "status": "success",
                "chunks": await db.execute(
                    f"SELECT COUNT(*) FROM r2r.document_chunks WHERE document_id = '{document.id}'"
                ).scalar()
            })
            
        except Exception as e:
            logger.error(f"Error ingesting {file.filename}: {str(e)}")
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/search")
async def search_documents(
    query: str,
    user_id: str = "default",
    limit: int = Query(10, ge=1, le=100),
    collection_id: Optional[str] = None,
    use_memory: bool = False,
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Search documents using semantic search"""
    
    services = req.app.state.services
    
    if not services.rag:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        # Search documents
        results = await services.rag.search_documents(
            db, user_id, query, limit, collection_id
        )
        
        # Optionally include memory context
        memory_results = []
        if use_memory and services.memory:
            try:
                memories = await services.memory.search_memories(
                    db, user_id, query, limit=5
                )
                memory_results = [
                    {
                        "type": "memory",
                        "content": mem.content,
                        "metadata": mem.metadata,
                        "created_at": mem.created_at.isoformat()
                    }
                    for mem in memories
                ]
            except Exception as e:
                logger.warning(f"Failed to search memories: {e}")
        
        return {
            "query": query,
            "documents": [
                {
                    "document_id": str(r["document"].id),
                    "filename": r["document"].filename,
                    "content": r["content"],
                    "similarity": r["similarity"],
                    "metadata": r["metadata"]
                }
                for r in results
            ],
            "memories": memory_results
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(
    user_id: str = Query(default="default"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """List user's documents"""
    
    services = req.app.state.services
    
    if not services.rag:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        documents = await services.rag.list_documents(
            db, user_id, limit, offset
        )
        
        return {
            "total": len(documents),
            "documents": [
                {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat(),
                    "is_processed": doc.is_processed
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Query(default="default"),
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    
    services = req.app.state.services
    
    if not services.rag:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        success = await services.rag.delete_document(
            db, document_id, user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"status": "success", "message": "Document deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Import Request
from fastapi import Request