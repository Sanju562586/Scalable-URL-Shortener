"""Repository for APIKey persistence and lookup."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.api_key import APIKey
from app.repositories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    """Data access layer for the api_keys table."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, APIKey)

    def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Find an API key record by its SHA-256 hash."""
        return (
            self._db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
            .first()
        )

    def deactivate(self, api_key: APIKey) -> APIKey:
        """Mark an API key as inactive (soft-delete)."""
        api_key.is_active = False
        self._db.flush()
        self._db.refresh(api_key)
        return api_key
