"""Pydantic schemas for API key creation and response."""

from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    """Payload for POST /api/v1/auth/api-keys."""

    owner: str = Field(..., min_length=1, max_length=255, description="Owner name or label.")


class APIKeyResponse(BaseModel):
    """
    Returned once at creation. The raw_key is never stored — the caller
    must save it immediately.
    """

    id: int
    raw_key: str = Field(..., description="Plain-text API key — shown only once.")
    owner: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyInfo(BaseModel):
    """Safe representation (no raw key) for listing/admin purposes."""

    id: int
    owner: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
