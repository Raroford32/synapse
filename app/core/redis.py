"""Redis client and helpers"""
from __future__ import annotations

from redis import asyncio as aioredis

from app.core.config import settings


redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis():
    """Dependency to get redis client"""
    yield redis


async def ping_redis() -> bool:
    try:
        return bool(await redis.ping())
    except Exception:
        return False

