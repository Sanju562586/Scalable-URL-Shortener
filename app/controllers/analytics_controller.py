"""
Analytics controller — GET /api/v1/analytics/{short_code}
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import db_session, rate_limited
from app.models.api_key import APIKey
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get(
    "/{short_code}",
    response_model=AnalyticsSummary,
    summary="Get analytics for a short URL",
    description=(
        "Returns click statistics for the given short code. "
        "The code must belong to the authenticated API key."
    ),
)
def get_analytics(
    short_code: str,
    db: Session = Depends(db_session),
    api_key: APIKey = Depends(rate_limited),
) -> AnalyticsSummary:
    service = AnalyticsService(db)
    return service.get_analytics(short_code, api_key.id)
