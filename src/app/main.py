import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded

from app import cache
from app.database import init_db
from app.limiter import limiter
from app.middleware.request_logger import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.logging import configure_logging
from app.utils.validation import validate_environment
from config import Config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate environment on startup
    if not os.getenv("TESTING"):
        validate_environment()
    configure_logging()
    # Skip real connections in test mode — tests supply their own DB session and mock Redis
    if not os.getenv("TESTING"):
        init_db(Config.DATABASE_URL)
        cache.redis_client = aioredis.from_url(Config.REDIS_URL, decode_responses=True)
    yield
    if cache.redis_client:
        await cache.redis_client.aclose()  # type: ignore[attr-defined]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Booking API",
        description="A RESTful booking API with JWT auth, Redis caching, and rate limiting.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,  # disabled — we serve both with pinned CDN versions below
        redoc_url=None,
    )

    # Add request size limits (100KB max)
    app.add_middleware(
        lambda app: app,
    )  # Placeholder for future middleware if needed

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Booking API — Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.4/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.4/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc() -> HTMLResponse:
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="Booking API — ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.4.0/bundles/redoc.standalone.js",
        )

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests", "retry_after": str(exc.detail)},
        )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Keep CORS as the outermost middleware so headers are present even on error responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        allow_credentials=True,
        max_age=3600,
    )

    from app.routes.auth import router as auth_router
    from app.routes.bookings import router as bookings_router
    from app.routes.health import router as health_router
    from app.routes.resources import router as resources_router

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(bookings_router, prefix="/api/bookings", tags=["Bookings"])
    app.include_router(resources_router, prefix="/api/resources", tags=["Resources"])
    app.include_router(health_router, tags=["Health"])

    return app


app = create_app()