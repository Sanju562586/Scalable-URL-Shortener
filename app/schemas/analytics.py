"""Pydantic schemas for click analytics responses."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class DailyClickCount(BaseModel):
    """Click count for a single day."""

    date: date
    clicks: int


class AnalyticsSummary(BaseModel):
    """Aggregated analytics for a short URL."""

    short_code: str
    original_url: str
    total_clicks: int
    unique_ips: int
    created_at: datetime
    expires_at: Optional[datetime]
    daily_breakdown: list[DailyClickCount]

    # Top referrers / user-agents (top 5)
    top_referers: list[dict]
    top_user_agents: list[dict]

    model_config = {"from_attributes": True}
