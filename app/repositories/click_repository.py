"""Repository for ClickEvent persistence and analytics aggregation."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.models.click import ClickEvent
from app.repositories.base import BaseRepository


class ClickRepository(BaseRepository[ClickEvent]):
    """Data access layer for the click_events table."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, ClickEvent)

    def bulk_create(self, events: list[ClickEvent]) -> None:
        """Insert multiple click events in a single flush."""
        self._db.add_all(events)
        self._db.flush()

    def count_by_url(self, url_id: int) -> int:
        """Total click count for a URL."""
        return (
            self._db.query(func.count(ClickEvent.id))
            .filter(ClickEvent.url_id == url_id)
            .scalar()
            or 0
        )

    def unique_ips_by_url(self, url_id: int) -> int:
        """Count of distinct IP addresses that clicked a URL."""
        return (
            self._db.query(func.count(func.distinct(ClickEvent.ip_address)))
            .filter(ClickEvent.url_id == url_id)
            .scalar()
            or 0
        )

    def daily_counts(
        self, url_id: int, days: int = 30
    ) -> list[dict]:
        """
        Click counts grouped by day for the last *days* days.

        Returns:
            List of {"date": date, "clicks": int} dicts, ordered ascending.
        """
        since = datetime.now(tz=timezone.utc) - timedelta(days=days)
        rows = (
            self._db.query(
                cast(ClickEvent.clicked_at, Date).label("day"),
                func.count(ClickEvent.id).label("clicks"),
            )
            .filter(ClickEvent.url_id == url_id, ClickEvent.clicked_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )
        return [{"date": row.day, "clicks": row.clicks} for row in rows]

    def top_referers(self, url_id: int, top_n: int = 5) -> list[dict]:
        """Top N referer strings by click count."""
        rows = (
            self._db.query(
                ClickEvent.referer,
                func.count(ClickEvent.id).label("clicks"),
            )
            .filter(ClickEvent.url_id == url_id, ClickEvent.referer.isnot(None))
            .group_by(ClickEvent.referer)
            .order_by(func.count(ClickEvent.id).desc())
            .limit(top_n)
            .all()
        )
        return [{"referer": row.referer, "clicks": row.clicks} for row in rows]

    def top_user_agents(self, url_id: int, top_n: int = 5) -> list[dict]:
        """Top N user-agent strings by click count."""
        rows = (
            self._db.query(
                ClickEvent.user_agent,
                func.count(ClickEvent.id).label("clicks"),
            )
            .filter(ClickEvent.url_id == url_id, ClickEvent.user_agent.isnot(None))
            .group_by(ClickEvent.user_agent)
            .order_by(func.count(ClickEvent.id).desc())
            .limit(top_n)
            .all()
        )
        return [{"user_agent": row.user_agent, "clicks": row.clicks} for row in rows]
