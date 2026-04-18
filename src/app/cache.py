import json
from functools import wraps
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request

redis_client: aioredis.Redis | None = None


def cache_response(ttl: int = 300, key_prefix: str = "cache"):
    def decorator(f: Callable):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # FastAPI injects all route params by name — request will always be in kwargs
            request: Request | None = kwargs.get("request")

            if redis_client is None or request is None:
                return await f(*args, **kwargs)

            cache_key = f"{key_prefix}:{request.url.path}?{request.url.query}"
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await f(*args, **kwargs)

            if isinstance(result, dict):
                await redis_client.setex(cache_key, ttl, json.dumps(result, default=str))

            return result
        return wrapper
    return decorator


async def invalidate_cache(pattern: str) -> None:
    if redis_client is None:
        return
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
