"""
AuthService — API key lifecycle management.

Responsibilities:
  • Generate raw key + hash and persist via APIKeyRepository.
  • Return the raw key once (caller must store it).
"""

from sqlalchemy.orm import Session

from app.models.api_key import APIKey
from app.repositories.api_key_repository import APIKeyRepository
from app.schemas.api_key import APIKeyCreateRequest, APIKeyResponse


class AuthService:
    """Business logic for API key management."""

    def __init__(self, db: Session) -> None:
        self._repo = APIKeyRepository(db)

    def create_api_key(self, request: APIKeyCreateRequest) -> APIKeyResponse:
        """
        Generate a new API key, hash it, and persist.

        The raw (plain-text) key is included in the response exactly once.
        Subsequent lookups only compare hashes.

        Returns:
            APIKeyResponse containing the one-time raw_key.
        """
        raw_key = APIKey.generate_raw_key()
        key_hash = APIKey.hash_key(raw_key)

        api_key_obj = APIKey(
            key_hash=key_hash,
            owner=request.owner,
            is_active=True,
        )
        created = self._repo.create(api_key_obj)
        self._repo.commit()

        return APIKeyResponse(
            id=created.id,
            raw_key=raw_key,  # ← only time the plain key appears
            owner=created.owner,
            is_active=created.is_active,
            created_at=created.created_at,
        )
