"""ORM models package — import all models here so Alembic can discover them."""

from app.models.api_key import APIKey  # noqa: F401
from app.models.url import URL         # noqa: F401
from app.models.click import ClickEvent  # noqa: F401

__all__ = ["APIKey", "URL", "ClickEvent"]
