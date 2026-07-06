"""
ClickEvent ORM model.
One row per redirect hit — stores metadata for analytics aggregation.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    url_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("urls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    referer: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    url: Mapped["URL"] = relationship("URL", back_populates="clicks")

    def __repr__(self) -> str:
        return f"<ClickEvent url_id={self.url_id} at={self.clicked_at}>"
