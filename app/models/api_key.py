"""
APIKey ORM model.
Raw keys are hashed (SHA-256) before storage; the plain-text key is
shown to the owner exactly once at creation time.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # back-reference
    urls: Mapped[list["URL"]] = relationship("URL", back_populates="api_key")

    # ── Class helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def generate_raw_key() -> str:
        """Generate a cryptographically secure 32-byte hex API key."""
        return secrets.token_hex(32)

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """SHA-256 hash of the raw key for safe storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} owner={self.owner!r}>"
