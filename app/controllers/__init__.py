"""Controllers package."""

from app.controllers.auth_controller import router as auth_router
from app.controllers.analytics_controller import router as analytics_router
from app.controllers.url_controller import api_router as url_api_router
from app.controllers.url_controller import redirect_router

__all__ = ["auth_router", "analytics_router", "url_api_router", "redirect_router"]
