"""
AnalyticsService — tracks clicks and aggregates statistics.

Responsibilities:
  • Record a ClickEvent row for every redirect.
  • Aggregate: total clicks, unique IPs, daily breakdown, top referers/UAs.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ShortCodeNotFound
from app.models.click import ClickEvent
from app.repositories.click_repository import ClickRepository
from app.repositories.url_repository import URLRepository
from app.schemas.analytics import AnalyticsSummary, DailyClickCount


class AnalyticsService:
    """Handles click recording and analytics retrieval."""

    def __init__(self, db: Session) -> None:
        self._click_repo = ClickRepository(db)
        self._url_repo = URLRepository(db)

    def record_click(
        self,
        url_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
    ) -> None:
        """
        Persist a single click event.

        Called immediately after a successful redirect.
        In a high-throughput scenario this could be queued via a background
        task, but we write synchronously here for correctness & simplicity.

        Args:
            url_id: Primary key of the URL that was redirected.
            ip_address: Client IP (may be None if behind proxies without headers).
            user_agent: HTTP User-Agent header value.
            referer: HTTP Referer header value.
        """
        event = ClickEvent(
            url_id=url_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )
        self._click_repo.create(event)
        self._click_repo.commit()

    def get_analytics(self, short_code: str, api_key_id: int) -> AnalyticsSummary:
        """
        Retrieve aggregated analytics for a short URL.

        Args:
            short_code: The short code to analyse.
            api_key_id: The requesting API key's ID (ownership check).

        Returns:
            AnalyticsSummary with total, unique, daily, and top-N breakdowns.

        Raises:
            ShortCodeNotFound: If the code doesn't exist or isn't owned by this key.
        """
        url_obj = self._url_repo.get_by_short_code(short_code)
        if url_obj is None or url_obj.api_key_id != api_key_id:
            raise ShortCodeNotFound(short_code)

        total = self._click_repo.count_by_url(url_obj.id)
        unique = self._click_repo.unique_ips_by_url(url_obj.id)
        daily_rows = self._click_repo.daily_counts(url_obj.id)
        top_referers = self._click_repo.top_referers(url_obj.id)
        top_uas = self._click_repo.top_user_agents(url_obj.id)

        return AnalyticsSummary(
            short_code=short_code,
            original_url=url_obj.original_url,
            total_clicks=total,
            unique_ips=unique,
            created_at=url_obj.created_at,
            expires_at=url_obj.expires_at,
            daily_breakdown=[
                DailyClickCount(date=r["date"], clicks=r["clicks"])
                for r in daily_rows
            ],
            top_referers=top_referers,
            top_user_agents=top_uas,
        )
