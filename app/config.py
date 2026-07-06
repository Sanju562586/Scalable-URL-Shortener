"""
Application configuration loaded from environment variables via pydantic-settings.
All settings have sensible defaults for local development.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the URL Shortener service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    base_url: str = "http://localhost:8000"
    short_code_min_length: int = 4

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql://postgres:password@localhost:5432/url_shortener"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_requests: int = 100       # max requests per window
    rate_limit_window_seconds: int = 60  # sliding window size (seconds)

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_ttl_seconds: int = 3600  # 1 hour default


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — safe to call repeatedly."""
    return Settings()
