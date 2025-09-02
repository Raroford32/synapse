#!/usr/bin/env python3
"""Initialize database with all required tables and extensions"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with all tables and extensions"""
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        # Create extensions
        logger.info("Creating PostgreSQL extensions...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        
        # Create schemas
        logger.info("Creating schemas...")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS r2r")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS mem0")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS shared")
        
        # Create all tables
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database initialized successfully!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())