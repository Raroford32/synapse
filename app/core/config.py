"""Application configuration"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # API
    API_KEY: str = "default-api-key"
    JWT_SECRET: str = "default-jwt-secret"
    
    # Database
    DATABASE_URL: str = "postgresql://synapse:synapse_password@localhost:5432/synapse_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenRouter Configuration (Primary LLM Provider)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_APP_NAME: str = "Synapse"
    OPENROUTER_SITE_URL: Optional[str] = None
    
    # OpenAI Configuration (For Embeddings Only)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Model Selection (via OpenRouter)
    DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    SMART_MODEL: str = "anthropic/claude-3-5-sonnet"
    FAST_MODEL: str = "meta-llama/llama-3-8b-instruct"
    CODE_MODEL: str = "anthropic/claude-3-5-sonnet"
    MODEL_SELECTION_STRATEGY: str = "auto"
    
    # Local models (optional)
    OLLAMA_HOST: Optional[str] = "http://localhost:11434"
    USE_LOCAL_MODELS: bool = False
    
    # Memory System
    MEM0_CONFIG_PATH: str = "/app/config/mem0.yaml"
    MEM0_VECTOR_STORE: str = "pgvector"
    
    # RAG System
    R2R_CONFIG_PATH: str = "/app/config/r2r.yaml"
    R2R_VECTOR_DIMENSION: int = 1536
    R2R_CHUNK_SIZE: int = 512
    R2R_CHUNK_OVERLAP: int = 50
    
    # MCP
    MCP_ENABLED: bool = True
    MCP_SERVER_PORT: int = 8001
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Optional services
    SENTRY_DSN: Optional[str] = None
    ENABLE_PROMETHEUS: bool = False
    PROMETHEUS_PORT: int = 9090
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_CONNECTION_TIMEOUT: int = 600
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_FILE_EXTENSIONS: str = "pdf,docx,txt,md,csv,json,xml,html,py,js,ts,java,cpp,go,rs,rb,php"
    
    # Cache
    CACHE_TTL_SECONDS: int = 3600
    CACHE_ENABLED: bool = True
    
    # Background Jobs
    ENABLE_BACKGROUND_JOBS: bool = True
    JOB_QUEUE_NAME: str = "synapse_jobs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate critical settings
if settings.ENVIRONMENT == "production":
    if settings.API_KEY == "default-api-key":
        raise ValueError("API_KEY must be set in production")
    if settings.JWT_SECRET == "default-jwt-secret":
        raise ValueError("JWT_SECRET must be set in production")
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY must be set")
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set for embeddings")