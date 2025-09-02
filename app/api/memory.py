"""Memory management endpoints"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "general"
    metadata: Optional[Dict[str, Any]] = {}


class ProfileUpdate(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    expertise_areas: Optional[list[str]] = None
    interaction_style: Optional[str] = None
    context_retention: Optional[str] = None


@router.post("/memory/{user_id}")
async def add_memory(
    user_id: str,
    memory: MemoryCreate,
    session_id: Optional[str] = None,
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Add a memory for a user"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        mem = await services.memory.add_memory(
            db,
            user_id,
            memory.content,
            memory.memory_type,
            session_id,
            memory.metadata
        )
        
        return {
            "id": str(mem.id),
            "content": mem.content,
            "memory_type": mem.memory_type,
            "created_at": mem.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding memory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/{user_id}")
async def get_memories(
    user_id: str,
    memory_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Get memories for a user"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        memories = await services.memory.get_memories(
            db, user_id, memory_type, session_id, limit
        )
        
        return {
            "user_id": user_id,
            "count": len(memories),
            "memories": [
                {
                    "id": str(mem.id),
                    "content": mem.content,
                    "memory_type": mem.memory_type,
                    "relevance_score": mem.relevance_score,
                    "access_count": mem.access_count,
                    "created_at": mem.created_at.isoformat(),
                    "metadata": mem.metadata
                }
                for mem in memories
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/{user_id}/search")
async def search_memories(
    user_id: str,
    query: str = Body(..., embed=True),
    limit: int = Query(10, ge=1, le=100),
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Search memories semantically"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        memories = await services.memory.search_memories(
            db, user_id, query, limit
        )
        
        return {
            "query": query,
            "count": len(memories),
            "memories": [
                {
                    "id": str(mem.id),
                    "content": mem.content,
                    "memory_type": mem.memory_type,
                    "relevance_score": mem.relevance_score,
                    "created_at": mem.created_at.isoformat()
                }
                for mem in memories
            ]
        }
        
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_user_profile(
    user_id: str,
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Get user profile"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        profile = await services.memory.get_user_profile(db, user_id)
        
        if not profile:
            return {
                "user_id": user_id,
                "exists": False
            }
        
        return {
            "user_id": user_id,
            "exists": True,
            "preferences": profile.preferences,
            "expertise_areas": profile.expertise_areas,
            "interaction_style": profile.interaction_style,
            "context_retention": profile.context_retention,
            "total_interactions": profile.total_interactions,
            "created_at": profile.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/{user_id}")
async def update_user_profile(
    user_id: str,
    updates: ProfileUpdate,
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        profile = await services.memory.update_user_profile(
            db, user_id, updates.dict(exclude_none=True)
        )
        
        return {
            "user_id": user_id,
            "preferences": profile.preferences,
            "expertise_areas": profile.expertise_areas,
            "interaction_style": profile.interaction_style,
            "context_retention": profile.context_retention,
            "updated_at": profile.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/{user_id}/consolidate")
async def consolidate_memories(
    user_id: str,
    req: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Consolidate similar memories to reduce redundancy"""
    
    services = req.app.state.services
    
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        await services.memory.consolidate_memories(db, user_id)
        
        return {
            "status": "success",
            "message": f"Memories consolidated for user {user_id}"
        }
        
    except Exception as e:
        logger.error(f"Error consolidating memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Import Request
from fastapi import Request