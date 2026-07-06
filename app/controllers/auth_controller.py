"""
Auth controller — POST /api/v1/auth/api-keys
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import db_session
from app.schemas.api_key import APIKeyCreateRequest, APIKeyResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new API key",
    description=(
        "Creates a new API key for the specified owner. "
        "The `raw_key` field is shown **exactly once** — store it securely."
    ),
)
def create_api_key(
    payload: APIKeyCreateRequest,
    db: Session = Depends(db_session),
) -> APIKeyResponse:
    service = AuthService(db)
    return service.create_api_key(payload)
