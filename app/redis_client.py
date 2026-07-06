"""
Redis connection pool and client factory.
Uses a module-level pool so all requests share connections.
"""

import redis
from app.config import get_settings

settings = get_settings()

# Module-level connection pool — created once at import time.
_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,  # keys/values returned as str, not bytes
    max_connections=50,
)


def get_redis() -> redis.Redis:
    """
    FastAPI dependency that returns a Redis client backed by the shared pool.
    The client itself is lightweight (no persistent connection held per call).

    Usage:
        cache: redis.Redis = Depends(get_redis)
    """
    return redis.Redis(connection_pool=_pool)
