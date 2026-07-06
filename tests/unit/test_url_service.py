"""Unit tests for URLService with mocked repositories and Redis."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.services.url_service import URLService
from app.schemas.url import URLCreateRequest
from app.models.url import URL
from app.models.api_key import APIKey
from app.core.exceptions import (
    CustomCodeConflict,
    ShortCodeExpired,
    ShortCodeInactive,
    ShortCodeNotFound,
    URLNotOwnedByKey,
)


def _make_url(
    id=1,
    short_code="abcd",
    original_url="https://example.com",
    is_active=True,
    expires_at=None,
    api_key_id=1,
) -> URL:
    url = URL()
    url.id = id
    url.short_code = short_code
    url.original_url = original_url
    url.is_active = is_active
    url.expires_at = expires_at
    url.api_key_id = api_key_id
    url.created_at = datetime.now(tz=timezone.utc)
    url.updated_at = datetime.now(tz=timezone.utc)
    return url


def _make_api_key(id=1) -> APIKey:
    k = APIKey()
    k.id = id
    k.key_hash = "abc"
    k.owner = "tester"
    k.is_active = True
    k.created_at = datetime.now(tz=timezone.utc)
    return k


@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def mock_cache():
    cache = MagicMock()
    cache.get.return_value = None  # cache miss by default
    return cache


@pytest.fixture()
def service(mock_db, mock_cache):
    return URLService(mock_db, mock_cache)


class TestResolve:
    """Cache-miss and cache-hit resolution paths."""

    def test_cache_hit_returns_cached_url(self, service, mock_cache):
        mock_cache.get.return_value = "https://cached.com"
        # Repo returns a valid active URL
        url = _make_url(short_code="abcd", original_url="https://cached.com")
        service._repo = MagicMock()
        service._repo.get_by_short_code_active.return_value = url

        result = service.resolve("abcd")
        assert result == "https://cached.com"

    def test_cache_miss_queries_db(self, service, mock_cache):
        mock_cache.get.return_value = None
        url = _make_url(original_url="https://db.com")
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = url

        result = service.resolve("abcd")
        assert result == "https://db.com"

    def test_cache_miss_not_found_raises(self, service, mock_cache):
        mock_cache.get.return_value = None
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = None

        with pytest.raises(ShortCodeNotFound):
            service.resolve("xxxx")

    def test_expired_url_raises(self, service, mock_cache):
        mock_cache.get.return_value = None
        past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        url = _make_url(expires_at=past)
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = url

        with pytest.raises(ShortCodeExpired):
            service.resolve("abcd")

    def test_inactive_url_raises(self, service, mock_cache):
        mock_cache.get.return_value = None
        url = _make_url(is_active=False)
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = url

        with pytest.raises(ShortCodeInactive):
            service.resolve("abcd")


class TestCreateShortURL:
    """URL creation with custom and auto-generated codes."""

    def test_custom_code_conflict_raises(self, service):
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = _make_url()  # exists

        req = URLCreateRequest(original_url="https://x.com", custom_code="taken")
        with pytest.raises(CustomCodeConflict):
            service.create_short_url(req, _make_api_key())

    def test_creates_with_auto_code(self, service):
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = None
        created = _make_url(id=5, short_code="__pending__")
        service._repo.create.return_value = created
        updated = _make_url(id=5, short_code="0005")
        service._repo.update_short_code.return_value = updated

        req = URLCreateRequest(original_url="https://new.com")
        result = service.create_short_url(req, _make_api_key())

        assert result.short_code == "0005"


class TestDeactivate:
    """Ownership-gated deactivation."""

    def test_deactivate_wrong_owner_raises(self, service):
        url = _make_url(api_key_id=99)
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = url

        with pytest.raises(URLNotOwnedByKey):
            service.deactivate("abcd", _make_api_key(id=1))

    def test_deactivate_not_found_raises(self, service):
        service._repo = MagicMock()
        service._repo.get_by_short_code.return_value = None

        with pytest.raises(ShortCodeNotFound):
            service.deactivate("xxxx", _make_api_key())
