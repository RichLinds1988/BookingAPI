import json
from functools import wraps
from flask import request, current_app
from app import redis_client


def cache_response(ttl: int = None, key_prefix: str = "cache"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Skip caching in test mode
            if current_app.config.get("TESTING"):
                return f(*args, **kwargs)

            cache_ttl = ttl or current_app.config.get("CACHE_TTL", 300)
            cache_key = f"{key_prefix}:{request.full_path}"

            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached), 200

            response = f(*args, **kwargs)

            if isinstance(response, tuple):
                resp_obj, status = response
            else:
                resp_obj, status = response, 200

            if status == 200:
                data = resp_obj.get_json() if hasattr(resp_obj, "get_json") else resp_obj
                redis_client.setex(cache_key, cache_ttl, json.dumps(data))

            return response

        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)