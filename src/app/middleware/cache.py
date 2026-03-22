import json
from functools import wraps
from flask import request, current_app
from app import redis_client


def cache_response(ttl: int = None, key_prefix: str = "cache"):
    """
    Decorator that caches a route's JSON response in Redis.
    Cache key is built from the prefix + full request path including query string.
    e.g. "resources:/api/resources?" or "availability:/api/bookings/availability/1?start=..."
    """
    def decorator(f):
        # @wraps preserves the original function's name and docstring
        # Without this, all decorated functions would appear as "wrapper" in logs/debuggers
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Skip caching in test mode — the test client returns response objects
            # that can't be serialized to JSON, and tests should hit real logic anyway
            if current_app.config.get("TESTING"):
                return f(*args, **kwargs)

            cache_ttl = ttl or current_app.config.get("CACHE_TTL", 300)

            # Build a unique cache key for this exact request URL
            cache_key = f"{key_prefix}:{request.full_path}"

            # Check if we already have a cached response for this key
            cached = redis_client.get(cache_key)
            if cached:
                # Return the cached JSON directly — no DB hit needed
                return json.loads(cached), 200

            # No cache hit — call the actual route function
            response = f(*args, **kwargs)

            # Routes return either a plain value or a (value, status_code) tuple
            if isinstance(response, tuple):
                resp_obj, status = response
            else:
                resp_obj, status = response, 200

            # Only cache successful responses — don't cache errors
            if status == 200:
                # Handle both Flask Response objects and plain dicts/lists
                data = resp_obj.get_json() if hasattr(resp_obj, "get_json") else resp_obj
                # setex stores the value and sets it to expire after cache_ttl seconds
                redis_client.setex(cache_key, cache_ttl, json.dumps(data))

            return response

        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Delete all Redis keys matching a pattern.
    Called after write operations to keep the cache consistent.
    e.g. invalidate_cache("bookings:*") clears all booking cache entries
    The * is a Redis wildcard — matches any characters after the prefix
    """
    keys = redis_client.keys(pattern)
    if keys:
        # The * unpacks the list so delete receives individual keys as arguments
        # rather than a single list argument
        redis_client.delete(*keys)
