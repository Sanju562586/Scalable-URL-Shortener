"""Repository for URL persistence, lookup, and ownership queries."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.url import URL
from app.repositories.base import BaseRepository


class URLRepository(BaseRepository[URL]):
    """Data access layer for the urls table."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, URL)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_by_short_code(self, short_code: str) -> Optional[URL]:
        """Return the URL row matching *short_code*, or None."""
        return (
            self._db.query(URL)
            .filter(URL.short_code == short_code)
            .first()
        )

    def get_by_short_code_active(self, short_code: str) -> Optional[URL]:
        """Return an active, non-expired URL row, or None."""
        return (
            self._db.query(URL)
            .filter(
                URL.short_code == short_code,
                URL.is_active.is_(True),
            )
            .first()
        )

    def get_by_api_key(
        self,
        api_key_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[URL], int]:
        """
        Paginated list of URLs owned by an API key.

        Returns:
            (items, total_count)
        """
        query = self._db.query(URL).filter(URL.api_key_id == api_key_id)
        total = query.count()
        items = query.order_by(URL.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    # ── Mutations ──────────────────────────────────────────────────────────────

    def update_short_code(self, url: URL, short_code: str) -> URL:
        """Set the short_code after initial insert (ID-based generation)."""
        url.short_code = short_code
        self._db.flush()
        self._db.refresh(url)
        return url

    def deactivate(self, url: URL) -> URL:
        """Soft-delete: set is_active=False."""
        url.is_active = False
        self._db.flush()
        self._db.refresh(url)
        return url
