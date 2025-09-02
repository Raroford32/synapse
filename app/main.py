"""
Synapse - Self-hosted AI backend for Cursor/Cline/Continue
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, memory, documents, health, websocket
from app.core.config import settings
from app.core.database import init_db
from app.core.services import ServiceManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if settings.LOG_FORMAT != 'json' else None
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Synapse...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized")
        
        # Initialize services
        app.state.services = ServiceManager()
        await app.state.services.initialize()
        
        logger.info("✅ Synapse is ready!")
        
    except Exception as e:
        logger.error(f"Failed to start Synapse: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Synapse...")
    
    try:
        if hasattr(app.state, 'services'):
            await app.state.services.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="Synapse",
    description="Self-hosted AI backend with persistent memory and RAG",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])
app.include_router(memory.router, prefix="/api", tags=["memory"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(websocket.router, tags=["websocket"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """OpenAI-compatible error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "invalid_request_error",
                "code": exc.status_code,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An unexpected error occurred",
                "type": "server_error",
                "code": 500,
            }
        },
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Synapse",
        "version": "0.1.0",
        "description": "Self-hosted AI backend for Cursor/Cline/Continue",
        "status": "running",
        "endpoints": {
            "openai_compatible": "/v1/chat/completions",
            "models": "/v1/models",
            "documents": "/api/ingest",
            "search": "/api/search",
            "memory": "/api/memory/{user_id}",
            "websocket": "/ws/chat/{user_id}",
            "health": "/health",
            "docs": "/docs" if settings.ENVIRONMENT == "development" else None,
        },
        "features": {
            "llm_provider": "OpenRouter",
            "embedding_provider": "OpenAI",
            "memory_system": "Mem0-style with PostgreSQL",
            "rag_system": "R2R-style with pgvector",
            "websocket": "Real-time streaming support",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )