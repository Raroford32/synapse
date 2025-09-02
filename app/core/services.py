"""Service manager for initializing all services"""
import logging
from typing import Optional

from app.core.config import settings
from app.services import LLMService, MemoryService, RagService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages all application services"""
    
    def __init__(self):
        self.llm: LLMService | None = None
        self.memory: MemoryService | None = None
        self.rag: RagService | None = None
        self.mcp = None
        
    async def initialize(self):
        """Initialize all services"""
        logger.info("Initializing services...")
        
        # Initialize LLM service
        await self._init_llm()
        
        # Initialize Memory service
        await self._init_memory()
        
        # Initialize RAG service
        await self._init_rag()
        
        # Initialize MCP service
        await self._init_mcp()
        
        logger.info("✅ All services initialized")
    
    async def _init_llm(self):
        """Initialize LiteLLM with available providers"""
        try:
            logger.info("Initializing LLM service...")
            self.llm = LLMService()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    async def _init_memory(self):
        """Initialize Mem0 memory system"""
        try:
            logger.info("Initializing Memory service...")
            self.memory = MemoryService()
        except Exception as e:
            logger.error(f"Failed to initialize Memory service: {e}")
            raise
    
    async def _init_rag(self):
        """Initialize R2R RAG system"""
        try:
            logger.info("Initializing RAG service...")
            self.rag = RagService()
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    async def _init_mcp(self):
        """Initialize MCP servers"""
        try:
            logger.info("Initializing MCP service...")
            
            # TODO: Import and initialize FastMCP
            # self.mcp = MCPService()
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP service: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup services on shutdown"""
        logger.info("Shutting down services...")
        
        # TODO: Implement cleanup for each service
        
        logger.info("✅ All services shut down")