"""Health check endpoints"""
import logging
from fastapi import APIRouter, Request
from datetime import datetime

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(req: Request):
    """Basic health check"""
    
    services = req.app.state.services
    
    # Get service health status
    service_health = services.check_health() if services else {
        "status": "unhealthy",
        "services": {}
    }
    
    return {
        "status": service_health["status"],
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "services": service_health["services"]
    }


@router.get("/health/detailed")
async def detailed_health_check(req: Request):
    """Detailed health check with service status"""
    
    services = req.app.state.services
    
    details = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "services": {}
    }
    
    # Check LLM service
    if services and services.llm:
        try:
            details["services"]["llm"] = {
                "status": "healthy",
                "provider": "OpenRouter",
                "models": {
                    "default": settings.DEFAULT_MODEL,
                    "smart": settings.SMART_MODEL,
                    "fast": settings.FAST_MODEL,
                    "code": settings.CODE_MODEL
                }
            }
        except Exception as e:
            details["services"]["llm"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        details["services"]["llm"] = {"status": "unavailable"}
    
    # Check Embedding service
    if services and services.embedding:
        try:
            details["services"]["embedding"] = {
                "status": "healthy",
                "provider": "OpenAI",
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "dimension": settings.R2R_VECTOR_DIMENSION
            }
        except Exception as e:
            details["services"]["embedding"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        details["services"]["embedding"] = {"status": "unavailable"}
    
    # Check Memory service
    if services and services.memory:
        details["services"]["memory"] = {
            "status": "healthy",
            "vector_store": settings.MEM0_VECTOR_STORE
        }
    else:
        details["services"]["memory"] = {"status": "unavailable"}
    
    # Check RAG service
    if services and services.rag:
        details["services"]["rag"] = {
            "status": "healthy",
            "chunk_size": settings.R2R_CHUNK_SIZE,
            "chunk_overlap": settings.R2R_CHUNK_OVERLAP
        }
    else:
        details["services"]["rag"] = {"status": "unavailable"}
    
    # Check MCP service
    if services and services.mcp:
        details["services"]["mcp"] = {
            "status": "healthy",
            "enabled": settings.MCP_ENABLED
        }
    else:
        details["services"]["mcp"] = {
            "status": "unavailable",
            "enabled": settings.MCP_ENABLED
        }
    
    # Determine overall status
    service_statuses = [s.get("status", "unavailable") for s in details["services"].values()]
    
    if all(s == "healthy" for s in service_statuses):
        details["status"] = "healthy"
    elif any(s == "healthy" for s in service_statuses):
        details["status"] = "degraded"
    else:
        details["status"] = "unhealthy"
    
    return details


@router.get("/ready")
async def readiness_check(req: Request):
    """Readiness check for Kubernetes"""
    
    services = req.app.state.services
    
    if not services:
        return {"ready": False, "reason": "Services not initialized"}
    
    # Check if critical services are ready
    if not services.llm:
        return {"ready": False, "reason": "LLM service not ready"}
    
    return {"ready": True}