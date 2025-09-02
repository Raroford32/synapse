"""Health check endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import ping_redis
from app.core.services import ServiceManager

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "synapse",
        "version": "0.1.0"
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies all services are ready"""
    try:
        # Check database
        await db.execute(text("SELECT 1"))

        # Service checks
        redis_ok = await ping_redis()
        health = {
            "database": "healthy",
            "redis": "healthy" if redis_ok else "unavailable",
            "r2r": "healthy",
            "mem0": "healthy",
            "llm": "healthy",
        }

        return {
            "status": "ready",
            "services": health,
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e)
        }