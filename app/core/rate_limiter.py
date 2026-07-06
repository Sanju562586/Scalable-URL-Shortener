"""
Sliding-window rate limiter backed by Redis.

Algorithm
---------
Uses a sorted set (ZSET) per API key where each member is a unique
request timestamp (float). On every request:

1. Remove members older than `window_seconds` ago  (expire old hits).
2. Count remaining members  → current request count in the window.
3. If count ≥ limit → reject with 429.
4. Otherwise add the new timestamp and set EXPIRY on the key.

This is a pure sliding-window: no bucket resets, no thunder-herd.

Key format:  rate:<api_key_hash>
"""

import time
from redis import Redis
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()


class RateLimiter:
    """
    Sliding-window rate limiter that uses Redis ZSETs.

    Attributes:
        redis: Active Redis client.
        limit: Maximum allowed requests per window.
        window: Window size in seconds.
    """

    def __init__(
        self,
        redis: Redis,
        limit: int | None = None,
        window: int | None = None,
    ) -> None:
        self._redis = redis
        self.limit = limit or settings.rate_limit_requests
        self.window = window or settings.rate_limit_window_seconds

    def _key(self, identifier: str) -> str:
        return f"rate:{identifier}"

    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check and record a request for *identifier*.

        Returns:
            (allowed: bool, remaining: int) — remaining requests in window.
        """
        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window

        pipe = self._redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", window_start)   # purge expired
        pipe.zcard(key)                                     # count remaining
        pipe.zadd(key, {str(now): now})                    # record this hit
        pipe.expire(key, self.window)                       # auto-expire key
        results = pipe.execute()

        current_count: int = results[1]  # before adding new hit
        allowed = current_count < self.limit
        remaining = max(0, self.limit - current_count - 1)
        return allowed, remaining

    def check(self, identifier: str) -> int:
        """
        Enforce rate limit; raises HTTP 429 if exceeded.

        Returns:
            Number of remaining requests in the current window.

        Raises:
            HTTPException(429): When the limit is exceeded.
        """
        allowed, remaining = self.is_allowed(identifier)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(self.window)},
            )
        return remaining
