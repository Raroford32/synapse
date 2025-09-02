"""Common middlewares: request id, metrics, basic rate limiting"""
from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response

from app.core.config import settings
from app.core.redis import redis


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.time()
    response: Response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = str(duration_ms)
    return response


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    # Simple IP-based limiter using Redis INCR with TTL
    try:
        key = f"rl:{request.client.host}:{int(time.time() // 60)}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.RATE_LIMIT_PER_MINUTE:
            return Response("Too Many Requests", status_code=429)
    except Exception:
        # Fail open if Redis unavailable
        pass
    return await call_next(request)

