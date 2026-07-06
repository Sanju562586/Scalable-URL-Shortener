"""
URL ORM model.
The short_code is derived from the auto-increment id via Base-62 encoding
(see app/core/encoder.py), ensuring uniqueness without collision checks.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    short_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    api_key: Mapped["APIKey"] = relationship("APIKey", back_populates="urls")
    clicks: Mapped[list["ClickEvent"]] = relationship(
        "ClickEvent", back_populates="url", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<URL short_code={self.short_code!r} -> {self.original_url[:40]!r}>"
