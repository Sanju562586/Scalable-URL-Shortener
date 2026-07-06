"""Unit tests for AnalyticsService with mocked repositories."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.analytics_service import AnalyticsService
from app.models.click import ClickEvent
from app.models.url import URL
from app.schemas.analytics import AnalyticsSummary, DailyClickCount
from app.core.exceptions import ShortCodeNotFound


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_url(
    id=1,
    short_code="abcd",
    original_url="https://example.com",
    api_key_id=1,
    is_active=True,
    expires_at=None,
) -> URL:
    url = URL()
    url.id = id
    url.short_code = short_code
    url.original_url = original_url
    url.api_key_id = api_key_id
    url.is_active = is_active
    url.expires_at = expires_at
    url.created_at = datetime.now(tz=timezone.utc)
    url.updated_at = datetime.now(tz=timezone.utc)
    return url


def _make_click_event(url_id=1, ip="1.2.3.4", ua="TestBrowser/1.0", referer=None) -> ClickEvent:
    event = ClickEvent()
    event.id = 1
    event.url_id = url_id
    event.ip_address = ip
    event.user_agent = ua
    event.referer = referer
    event.clicked_at = datetime.now(tz=timezone.utc)
    return event


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def service(mock_db):
    svc = AnalyticsService(mock_db)
    # Replace the internal repos with mocks
    svc._click_repo = MagicMock()
    svc._url_repo = MagicMock()
    return svc


# ── Tests: record_click ───────────────────────────────────────────────────────

class TestRecordClick:
    """AnalyticsService.record_click() — persists a ClickEvent row."""

    def test_record_click_creates_event(self, service):
        """record_click should create and commit a ClickEvent."""
        service.record_click(
            url_id=42,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            referer="https://referrer.com",
        )
        service._click_repo.create.assert_called_once()
        service._click_repo.commit.assert_called_once()

    def test_record_click_stores_all_metadata(self, service):
        """Verify the ClickEvent is constructed with all provided fields."""
        service.record_click(
            url_id=7,
            ip_address="192.168.1.1",
            user_agent="curl/7.0",
            referer="https://example.org",
        )
        created_event: ClickEvent = service._click_repo.create.call_args[0][0]
        assert created_event.url_id == 7
        assert created_event.ip_address == "192.168.1.1"
        assert created_event.user_agent == "curl/7.0"
        assert created_event.referer == "https://example.org"

    def test_record_click_handles_none_metadata(self, service):
        """record_click should work fine with all None optional fields."""
        service.record_click(url_id=1)
        created_event: ClickEvent = service._click_repo.create.call_args[0][0]
        assert created_event.ip_address is None
        assert created_event.user_agent is None
        assert created_event.referer is None


# ── Tests: get_analytics ──────────────────────────────────────────────────────

class TestGetAnalytics:
    """AnalyticsService.get_analytics() — aggregates stats for a URL."""

    def _setup_service_returns(
        self,
        service,
        url=None,
        total=10,
        unique=5,
        daily=None,
        referers=None,
        uas=None,
    ):
        """Helper that wires up standard mock return values."""
        service._url_repo.get_by_short_code.return_value = url or _make_url()
        service._click_repo.count_by_url.return_value = total
        service._click_repo.unique_ips_by_url.return_value = unique
        service._click_repo.daily_counts.return_value = daily or [
            {"date": datetime.now(tz=timezone.utc).date(), "clicks": total}
        ]
        service._click_repo.top_referers.return_value = referers or []
        service._click_repo.top_user_agents.return_value = uas or []

    def test_returns_analytics_summary(self, service):
        """get_analytics should return a fully populated AnalyticsSummary."""
        url = _make_url(id=1, short_code="abcd", api_key_id=99)
        self._setup_service_returns(service, url=url, total=20, unique=8)

        result = service.get_analytics("abcd", api_key_id=99)

        assert isinstance(result, AnalyticsSummary)
        assert result.short_code == "abcd"
        assert result.total_clicks == 20
        assert result.unique_ips == 8
        assert result.original_url == "https://example.com"

    def test_raises_not_found_for_unknown_code(self, service):
        """get_analytics should raise ShortCodeNotFound for unknown codes."""
        service._url_repo.get_by_short_code.return_value = None

        with pytest.raises(ShortCodeNotFound):
            service.get_analytics("unknown", api_key_id=1)

    def test_raises_not_found_for_wrong_owner(self, service):
        """get_analytics raises ShortCodeNotFound if api_key_id doesn't match."""
        url = _make_url(api_key_id=99)
        service._url_repo.get_by_short_code.return_value = url

        with pytest.raises(ShortCodeNotFound):
            service.get_analytics("abcd", api_key_id=1)  # wrong owner

    def test_daily_breakdown_is_populated(self, service):
        """Daily click breakdown should be mapped into DailyClickCount objects."""
        from datetime import date
        daily_data = [
            {"date": date(2024, 1, 1), "clicks": 5},
            {"date": date(2024, 1, 2), "clicks": 3},
        ]
        self._setup_service_returns(service, daily=daily_data)

        result = service.get_analytics("abcd", api_key_id=1)

        assert len(result.daily_breakdown) == 2
        assert result.daily_breakdown[0].clicks == 5
        assert result.daily_breakdown[1].clicks == 3

    def test_top_referers_are_included(self, service):
        """Top referrers from the repository should appear in the summary."""
        referers = [
            {"referer": "https://twitter.com", "clicks": 8},
            {"referer": "https://google.com", "clicks": 3},
        ]
        self._setup_service_returns(service, referers=referers)

        result = service.get_analytics("abcd", api_key_id=1)

        assert len(result.top_referers) == 2
        assert result.top_referers[0]["referer"] == "https://twitter.com"

    def test_zero_clicks_returns_valid_summary(self, service):
        """A URL with zero clicks should return a valid summary with zeros."""
        self._setup_service_returns(service, total=0, unique=0, daily=[])

        result = service.get_analytics("abcd", api_key_id=1)

        assert result.total_clicks == 0
        assert result.unique_ips == 0
        assert result.daily_breakdown == []

    def test_expires_at_included_in_summary(self, service):
        """expires_at should be propagated from the URL object."""
        expiry = datetime.now(tz=timezone.utc) + timedelta(days=30)
        url = _make_url(expires_at=expiry)
        self._setup_service_returns(service, url=url)

        result = service.get_analytics("abcd", api_key_id=1)

        assert result.expires_at == expiry
