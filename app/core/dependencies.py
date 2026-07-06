"""
FastAPI dependency functions.

Centralises:
  • DB session injection
  • Redis client injection
  • API key authentication
  • Rate limiting enforcement
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session
from redis import Redis

from app.database import get_db
from app.redis_client import get_redis
from app.core.exceptions import InvalidAPIKey
from app.core.rate_limiter import RateLimiter
from app.models.api_key import APIKey


# ── Database & Cache ──────────────────────────────────────────────────────────

def db_session(db: Session = Depends(get_db)) -> Session:
    """Re-export for convenient import in controllers."""
    return db


def redis_client(cache: Redis = Depends(get_redis)) -> Redis:
    """Re-export for convenient import in controllers."""
    return cache


# ── Authentication ────────────────────────────────────────────────────────────

def get_api_key(
    x_api_key: str = Header(..., alias="X-API-Key", description="Your API key"),
    db: Session = Depends(get_db),
) -> APIKey:
    """
    Validate the X-API-Key header against hashed keys in the database.

    Returns the matching APIKey ORM object.
    Raises InvalidAPIKey (HTTP 401) if the key is absent or unrecognised.
    """
    from app.repositories.api_key_repository import APIKeyRepository

    key_hash = APIKey.hash_key(x_api_key)
    repo = APIKeyRepository(db)
    api_key_obj = repo.get_by_hash(key_hash)

    if api_key_obj is None or not api_key_obj.is_active:
        raise InvalidAPIKey()

    return api_key_obj


# ── Rate Limiting ─────────────────────────────────────────────────────────────

def rate_limited(
    api_key: APIKey = Depends(get_api_key),
    cache: Redis = Depends(get_redis),
) -> APIKey:
    """
    Authenticate *and* enforce sliding-window rate limiting per API key.
    Use this as the dependency for write/read endpoints that need both.

    Returns:
        The authenticated APIKey ORM object.
    """
    limiter = RateLimiter(cache)
    limiter.check(identifier=api_key.key_hash)
    return api_key
