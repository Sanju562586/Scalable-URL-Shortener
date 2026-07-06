"""
FastAPI application factory and entry point.

Run locally:
    uvicorn app.main:app --reload

Environment variables are loaded from .env (see .env.example).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.controllers import (
    auth_router,
    analytics_router,
    url_api_router,
    redirect_router,
)
from app.middleware import LoggingMiddleware

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("url_shortener")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    logger.info("Starting URL Shortener (env=%s)", settings.app_env)
    yield
    logger.info("Shutting down URL Shortener")


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Scalable URL Shortener & Analytics Service",
        description=(
            "REST API for URL shortening, redirection, and click analytics. "
            "Authenticate with `X-API-Key` header."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    # Order matters: management routes before the catch-all redirect route.
    app.include_router(auth_router)
    app.include_router(url_api_router)
    app.include_router(analytics_router)
    app.include_router(redirect_router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/api/v1/health", tags=["Health"], summary="Health check")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "1.0.0"})

    return app


app = create_app()
