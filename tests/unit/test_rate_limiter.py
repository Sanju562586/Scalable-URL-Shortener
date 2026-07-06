"""Unit tests for the sliding-window RateLimiter."""

import time
import pytest
import fakeredis
from fastapi import HTTPException

from app.core.rate_limiter import RateLimiter


@pytest.fixture()
def redis():
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield client
    client.flushall()


def test_allows_requests_under_limit(redis):
    limiter = RateLimiter(redis, limit=5, window=60)
    for _ in range(5):
        allowed, remaining = limiter.is_allowed("user-1")
        assert allowed is True


def test_blocks_request_over_limit(redis):
    limiter = RateLimiter(redis, limit=3, window=60)
    for _ in range(3):
        limiter.is_allowed("user-2")
    allowed, remaining = limiter.is_allowed("user-2")
    assert allowed is False
    assert remaining == 0


def test_check_raises_429_when_exceeded(redis):
    limiter = RateLimiter(redis, limit=1, window=60)
    limiter.check("user-3")  # first — ok
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user-3")  # second — blocked
    assert exc_info.value.status_code == 429


def test_different_identifiers_are_independent(redis):
    limiter = RateLimiter(redis, limit=2, window=60)
    limiter.check("user-a")
    limiter.check("user-a")
    # user-b is fresh
    allowed, _ = limiter.is_allowed("user-b")
    assert allowed is True


def test_remaining_decrements(redis):
    limiter = RateLimiter(redis, limit=5, window=60)
    _, r1 = limiter.is_allowed("user-4")
    _, r2 = limiter.is_allowed("user-4")
    assert r2 < r1


def test_retry_after_header_present(redis):
    limiter = RateLimiter(redis, limit=1, window=30)
    limiter.check("user-5")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user-5")
    assert "Retry-After" in exc_info.value.headers
    assert exc_info.value.headers["Retry-After"] == "30"
