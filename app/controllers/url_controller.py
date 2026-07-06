"""
URL controller — short URL creation, redirect, deactivation, and listing.

Routes
------
POST   /api/v1/shorten          — create a short URL
GET    /{short_code}            — redirect (HTTP 302) + record click
DELETE /api/v1/urls/{code}      — deactivate a short URL
GET    /api/v1/urls             — list URLs owned by the API key

Route ordering note
--------------------
The redirect_router is registered LAST in main.py so FastAPI evaluates all
``/api/v1/*`` and ``/docs`` routes before falling through to the catch-all
``/{short_code}`` pattern.  We also guard against reserved path prefixes
explicitly in the handler itself.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.core.dependencies import db_session, rate_limited, redis_client
from app.models.api_key import APIKey
from app.schemas.url import URLCreateRequest, URLListResponse, URLResponse
from app.services.analytics_service import AnalyticsService
from app.services.url_service import URLService

# Paths that must NEVER be interpreted as short codes.
_RESERVED_PREFIXES = ("api", "docs", "redoc", "openapi.json", "favicon.ico")

# Redirect router lives at root level (no /api/v1 prefix) so short URLs
# are served at /<code> directly.
redirect_router = APIRouter(tags=["Redirect"])

# All management routes live under /api/v1
api_router = APIRouter(prefix="/api/v1", tags=["URLs"])


@api_router.post(
    "/shorten",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
)
def shorten_url(
    payload: URLCreateRequest,
    db: Session = Depends(db_session),
    cache: Redis = Depends(redis_client),
    api_key: APIKey = Depends(rate_limited),
) -> URLResponse:
    """Create a new short URL. Requires a valid X-API-Key header."""
    service = URLService(db, cache)
    return service.create_short_url(payload, api_key)


@redirect_router.get(
    "/{short_code}",
    summary="Redirect to original URL",
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect to original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "Short URL expired or inactive"},
    },
)
def redirect(
    short_code: str,
    request: Request,
    db: Session = Depends(db_session),
    cache: Redis = Depends(redis_client),
) -> RedirectResponse:
    """
    Resolve a short code to its original URL and redirect (302).
    Records a click event with client metadata.

    Raises HTTP 404 immediately for reserved path segments so the route
    doesn't accidentally swallow ``/docs`` or ``/api/*`` requests in
    misconfigured deployments.
    """
    # Guard against reserved paths reaching this handler
    if short_code.split("/")[0].lower() in _RESERVED_PREFIXES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    url_service = URLService(db, cache)
    analytics_service = AnalyticsService(db)

    original_url = url_service.resolve(short_code)

    # Look up the URL object to record click metadata
    url_obj = url_service._repo.get_by_short_code(short_code)
    if url_obj:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        referer = request.headers.get("referer")
        analytics_service.record_click(
            url_id=url_obj.id,
            ip_address=ip,
            user_agent=ua,
            referer=referer,
        )

    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)


@api_router.delete(
    "/urls/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a short URL",
)
def deactivate_url(
    short_code: str,
    db: Session = Depends(db_session),
    cache: Redis = Depends(redis_client),
    api_key: APIKey = Depends(rate_limited),
) -> Response:
    """Soft-delete a short URL. Only the owning API key may deactivate it."""
    service = URLService(db, cache)
    service.deactivate(short_code, api_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api_router.get(
    "/urls",
    response_model=URLListResponse,
    summary="List your short URLs",
)
def list_urls(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(db_session),
    cache: Redis = Depends(redis_client),
    api_key: APIKey = Depends(rate_limited),
) -> URLListResponse:
    """Paginated list of all short URLs belonging to the authenticated API key."""
    service = URLService(db, cache)
    return service.list_urls(api_key, page=page, page_size=page_size)
