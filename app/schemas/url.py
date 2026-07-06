"""Pydantic schemas for URL creation, response, and listing."""

from datetime import datetime
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class URLCreateRequest(BaseModel):
    """Payload for POST /api/v1/shorten."""

    original_url: AnyHttpUrl = Field(..., description="The long URL to shorten.")
    custom_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional custom alias. Auto-generated if omitted.",
    )
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiry timestamp (UTC)."
    )

    @field_validator("original_url", mode="before")
    @classmethod
    def stringify_url(cls, v):
        return str(v) if not isinstance(v, str) else v


class URLResponse(BaseModel):
    """Response body after creating or fetching a short URL."""

    short_code: str
    short_url: str
    original_url: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class URLListResponse(BaseModel):
    """Paginated list of URLs belonging to an API key."""

    items: list[URLResponse]
    total: int
    page: int
    page_size: int
