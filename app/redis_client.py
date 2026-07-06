"""
Redis connection pool and client factory.
Uses a module-level pool so all requests share connections.

For Upstash (and any rediss:// TLS endpoint), ssl_cert_reqs is set to
"none" to bypass certificate validation — required on Windows where
Python's default ssl cert store may not include the remote CA.
"""

import logging
import redis

from app.config import get_settings

logger = logging.getLogger("url_shortener.redis")
settings = get_settings()

# Module-level connection pool — created once at import time.
# ssl_cert_reqs="none" is required for Upstash rediss:// on Windows.
_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,   # keys/values returned as str, not bytes
    max_connections=50,
    ssl_cert_reqs="none",    # disable cert verification for Upstash TLS
)


def get_redis() -> redis.Redis:
    """
    FastAPI dependency that returns a Redis client backed by the shared pool.
    The client itself is lightweight (no persistent connection held per call).

    Usage:
        cache: redis.Redis = Depends(get_redis)
    """
    return redis.Redis(connection_pool=_pool)
