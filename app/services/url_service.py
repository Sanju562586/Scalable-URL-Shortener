"""
URLService — core business logic for URL shortening and redirection.

Responsibilities:
  • Create short URLs using Base-62 encoding of the DB row ID.
  • Resolve short codes: cache-first (Redis), DB fallback.
  • Write-through cache invalidation on deactivation.
  • Validate expiry and active status on each redirect.
"""

from datetime import datetime, timezone
from typing import Optional

from redis import Redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.encoder import encode_padded
from app.core.exceptions import (
    CustomCodeConflict,
    ShortCodeExpired,
    ShortCodeInactive,
    ShortCodeNotFound,
    URLNotOwnedByKey,
)
from app.models.api_key import APIKey
from app.models.url import URL
from app.repositories.url_repository import URLRepository
from app.schemas.url import URLCreateRequest, URLListResponse, URLResponse

settings = get_settings()


class URLService:
    """
    Handles URL creation, resolution, listing, and deactivation.

    Cache strategy
    --------------
    Redis key: ``url:<short_code>``  → original URL string
    TTL: ``settings.cache_ttl_seconds`` (default 1 h), refreshed on every hit.
    On cache miss the DB is queried and the result is cached.
    On deactivation the cache key is deleted immediately.
    """

    def __init__(self, db: Session, cache: Redis) -> None:
        self._repo = URLRepository(db)
        self._cache = cache

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _cache_key(self, short_code: str) -> str:
        return f"url:{short_code}"

    def _cache_get(self, short_code: str) -> Optional[str]:
        return self._cache.get(self._cache_key(short_code))

    def _cache_set(self, short_code: str, original_url: str) -> None:
        self._cache.setex(
            self._cache_key(short_code),
            settings.cache_ttl_seconds,
            original_url,
        )

    def _cache_delete(self, short_code: str) -> None:
        self._cache.delete(self._cache_key(short_code))

    # ── Public API ────────────────────────────────────────────────────────────

    def create_short_url(
        self,
        request: URLCreateRequest,
        api_key: APIKey,
    ) -> URLResponse:
        """
        Create and persist a new short URL.

        If *request.custom_code* is provided, it is used as the short code
        (conflict → HTTP 409).  Otherwise, the auto-increment ID is Base-62
        encoded after the first insert.

        Args:
            request: Validated URLCreateRequest payload.
            api_key: The authenticated owner APIKey object.

        Returns:
            URLResponse with the generated short_url.
        """
        # Validate custom code uniqueness before insert.
        if request.custom_code:
            existing = self._repo.get_by_short_code(request.custom_code)
            if existing:
                raise CustomCodeConflict(request.custom_code)

        url_obj = URL(
            short_code=request.custom_code or "__pending__",
            original_url=str(request.original_url),
            api_key_id=api_key.id,
            is_active=True,
            expires_at=request.expires_at,
        )
        created = self._repo.create(url_obj)

        # Generate Base-62 code from the now-known primary key.
        if not request.custom_code:
            short_code = encode_padded(created.id, settings.short_code_min_length)
            created = self._repo.update_short_code(created, short_code)

        self._repo.commit()
        self._cache_set(created.short_code, created.original_url)

        return self._to_response(created)

    def resolve(self, short_code: str) -> str:
        """
        Resolve a short code to its original URL.

        Checks Redis first; falls back to DB on cache miss.
        Validates active status and expiry on every resolution.

        Args:
            short_code: The Base-62 short code.

        Returns:
            The original (long) URL string.

        Raises:
            ShortCodeNotFound, ShortCodeInactive, ShortCodeExpired
        """
        # ── Cache hit ──
        cached = self._cache_get(short_code)
        if cached:
            # Still validate in DB for is_active / expiry on cache hit
            # Use a lightweight existence check rather than skipping entirely.
            url_obj = self._repo.get_by_short_code_active(short_code)
            if url_obj is None:
                self._cache_delete(short_code)
                raise ShortCodeNotFound(short_code)
            self._validate_url(url_obj, short_code)
            # Refresh TTL on hot path
            self._cache_set(short_code, cached)
            return cached

        # ── Cache miss — query DB ──
        url_obj = self._repo.get_by_short_code(short_code)
        if url_obj is None:
            raise ShortCodeNotFound(short_code)

        self._validate_url(url_obj, short_code)
        self._cache_set(short_code, url_obj.original_url)
        return url_obj.original_url

    def deactivate(self, short_code: str, api_key: APIKey) -> None:
        """
        Deactivate (soft-delete) a short URL.

        Args:
            short_code: The code to deactivate.
            api_key: Must be the owner of the URL.

        Raises:
            ShortCodeNotFound, URLNotOwnedByKey
        """
        url_obj = self._repo.get_by_short_code(short_code)
        if url_obj is None:
            raise ShortCodeNotFound(short_code)
        if url_obj.api_key_id != api_key.id:
            raise URLNotOwnedByKey()

        self._repo.deactivate(url_obj)
        self._repo.commit()
        self._cache_delete(short_code)

    def list_urls(
        self, api_key: APIKey, page: int = 1, page_size: int = 20
    ) -> URLListResponse:
        """Paginated list of URLs owned by *api_key*."""
        skip = (page - 1) * page_size
        items, total = self._repo.get_by_api_key(api_key.id, skip, page_size)
        return URLListResponse(
            items=[self._to_response(u) for u in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate_url(self, url_obj: URL, short_code: str) -> None:
        """Raise appropriate exception if URL is unusable."""
        if not url_obj.is_active:
            raise ShortCodeInactive(short_code)
        if url_obj.expires_at and url_obj.expires_at < datetime.now(tz=timezone.utc):
            raise ShortCodeExpired(short_code)

    def _to_response(self, url_obj: URL) -> URLResponse:
        short_url = f"{settings.base_url}/{url_obj.short_code}"
        return URLResponse(
            short_code=url_obj.short_code,
            short_url=short_url,
            original_url=url_obj.original_url,
            is_active=url_obj.is_active,
            expires_at=url_obj.expires_at,
            created_at=url_obj.created_at,
        )
