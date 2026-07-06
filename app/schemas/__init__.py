"""Schemas package."""

from app.schemas.url import URLCreateRequest, URLResponse, URLListResponse
from app.schemas.api_key import APIKeyCreateRequest, APIKeyResponse, APIKeyInfo
from app.schemas.analytics import AnalyticsSummary, DailyClickCount

__all__ = [
    "URLCreateRequest", "URLResponse", "URLListResponse",
    "APIKeyCreateRequest", "APIKeyResponse", "APIKeyInfo",
    "AnalyticsSummary", "DailyClickCount",
]
