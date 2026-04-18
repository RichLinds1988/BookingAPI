import json
import logging
from functools import wraps
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request
from redis.exceptions import RedisError

redis_client: aioredis.Redis | None = None
logger = logging.getLogger("app.cache")


def cache_response(ttl: int = 300, key_prefix: str = "cache"):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI injects all route params by name — request will always be in kwargs
            request: Request | None = kwargs.get("request")

            if redis_client is None or request is None:
                return await func(*args, **kwargs)

            cache_key = f"{key_prefix}:{request.url.path}?{request.url.query}"
            # Include user ID in key if authenticated to prevent data leakage
            current_user = kwargs.get("current_user")
            if current_user and hasattr(current_user, "id"):
                cache_key += f":user_{current_user.id}"
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except RedisError:
                # Fail open if Redis is unavailable so API endpoints still respond.
                return await func(*args, **kwargs)

            result = await func(*args, **kwargs)

            if isinstance(result, dict):
                try:
                    await redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
                except RedisError:
                    # Cache write failures should never fail the request path.
                    logger.warning("Failed to write response to cache", exc_info=True)

            return result

        return wrapper

    return decorator


async def invalidate_cache(pattern: str) -> None:
    if redis_client is None:
        return
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
