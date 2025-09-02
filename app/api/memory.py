"""Memory management endpoints"""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel

from app.core.auth import require_api_key
from app.core.services import ServiceManager
from fastapi import Request

router = APIRouter(dependencies=[Depends(require_api_key)])


class MemoryCreate(BaseModel):
    content: str
    type: str = "general"
    metadata: Optional[dict] = None


@router.get("/memory/{user_id}")
async def get_user_memory(
    user_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Get all memories for a user"""
    services: ServiceManager = request.app.state.services
    memories = await services.memory.list_memories(user_id)
    return {"user_id": user_id, "memories": memories, "count": len(memories)}


@router.post("/memory/{user_id}")
async def create_memory(
    user_id: str,
    memory: MemoryCreate,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Create a new memory for a user"""
    services: ServiceManager = request.app.state.services
    created = await services.memory.create_memory(
        user_id=user_id,
        content=memory.content,
        type=memory.type,
        metadata=memory.metadata,
    )
    return {"status": "created", "user_id": user_id, "memory_id": created["id"], "memory": created}


@router.delete("/memory/{user_id}/{memory_id}")
async def delete_memory(
    user_id: str,
    memory_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Delete a specific memory"""
    services: ServiceManager = request.app.state.services
    ok = await services.memory.delete_memory(user_id, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "memory_id": memory_id}