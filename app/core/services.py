"""Service manager for initializing all services"""
import logging
from typing import Optional

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.memory_service import MemoryService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages all application services"""
    
    def __init__(self):
        self.llm: Optional[LLMService] = None
        self.embedding: Optional[EmbeddingService] = None
        self.memory: Optional[MemoryService] = None
        self.rag: Optional[RAGService] = None
        self.mcp = None  # TODO: Implement MCP service
        
    async def initialize(self):
        """Initialize all services"""
        logger.info("Initializing services...")
        
        try:
            # Initialize Embedding service first (needed by others)
            await self._init_embedding()
            
            # Initialize LLM service
            await self._init_llm()
            
            # Initialize Memory service
            await self._init_memory()
            
            # Initialize RAG service
            await self._init_rag()
            
            # Initialize MCP service
            await self._init_mcp()
            
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise
    
    async def _init_embedding(self):
        """Initialize OpenAI Embedding service"""
        try:
            logger.info("Initializing Embedding service...")
            
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not configured - embeddings will not work")
                return
            
            self.embedding = EmbeddingService()
            
            # Test embedding service
            test_embedding = await self.embedding.generate_embedding("test")
            if test_embedding:
                logger.info(f"✅ Embedding service initialized (dimension: {len(test_embedding)})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Embedding service: {e}")
            # Don't raise - allow system to work without embeddings
    
    async def _init_llm(self):
        """Initialize OpenRouter LLM service"""
        try:
            logger.info("Initializing LLM service with OpenRouter...")
            
            if not settings.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is required")
            
            self.llm = LLMService()
            
            # Log available models
            logger.info(f"Available models via OpenRouter:")
            logger.info(f"  - Default: {settings.DEFAULT_MODEL}")
            logger.info(f"  - Smart: {settings.SMART_MODEL}")
            logger.info(f"  - Fast: {settings.FAST_MODEL}")
            logger.info(f"  - Code: {settings.CODE_MODEL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    async def _init_memory(self):
        """Initialize Mem0-style memory system"""
        try:
            logger.info("Initializing Memory service...")
            
            if not self.embedding:
                logger.warning("Embedding service not available - memory search will be limited")
            
            self.memory = MemoryService(self.embedding)
            logger.info("✅ Memory service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Memory service: {e}")
            raise
    
    async def _init_rag(self):
        """Initialize R2R-style RAG system"""
        try:
            logger.info("Initializing RAG service...")
            
            if not self.embedding:
                logger.warning("Embedding service not available - RAG search will be limited")
            
            self.rag = RAGService(self.embedding)
            logger.info("✅ RAG service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    async def _init_mcp(self):
        """Initialize MCP servers"""
        try:
            if not settings.MCP_ENABLED:
                logger.info("MCP is disabled in configuration")
                return
            
            logger.info("Initializing MCP service...")
            
            # TODO: Implement FastMCP integration
            # from app.services.mcp_service import MCPService
            # self.mcp = MCPService()
            # await self.mcp.initialize()
            
            logger.info("⚠️ MCP service not yet implemented")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP service: {e}")
            # Don't raise - MCP is optional
    
    async def shutdown(self):
        """Cleanup services on shutdown"""
        logger.info("Shutting down services...")
        
        try:
            # Cleanup LLM service
            if self.llm and hasattr(self.llm, 'client'):
                await self.llm.client.aclose()
            
            # Cleanup other services as needed
            # ...
            
            logger.info("✅ All services shut down")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
    
    def check_health(self) -> dict:
        """Check health status of all services"""
        
        health = {
            "status": "healthy",
            "services": {
                "llm": "healthy" if self.llm else "unavailable",
                "embedding": "healthy" if self.embedding else "unavailable",
                "memory": "healthy" if self.memory else "unavailable",
                "rag": "healthy" if self.rag else "unavailable",
                "mcp": "healthy" if self.mcp else "unavailable",
            }
        }
        
        # Overall status
        if all(status == "healthy" for status in health["services"].values()):
            health["status"] = "healthy"
        elif any(status == "healthy" for status in health["services"].values()):
            health["status"] = "degraded"
        else:
            health["status"] = "unhealthy"
        
        return health