from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.database import close_db, init_db
from app.core.redis_client import close_redis, get_redis

configure_logging()
log = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    log.info("startup_begin", env=settings.APP_ENV)

    # Initialize database tables (dev only; prod should use Alembic migrations)
    if settings.APP_ENV in ("development", "testing"):
        try:
            await init_db()
            log.info("database_initialized")
        except Exception as exc:
            log.warning("database_init_failed", error=str(exc))

    # Warm up Redis connection
    try:
        redis = get_redis()
        await redis.ping()
        log.info("redis_connected")
    except Exception as exc:
        log.warning("redis_connection_failed", error=str(exc))

    log.info("startup_complete")
    yield

    # Shutdown
    log.info("shutdown_begin")
    await close_db()
    await close_redis()
    log.info("shutdown_complete")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="WebScrapy AI Platform API",
    description=(
        "AI-powered web scraping platform with intelligent selector generation, "
        "auto-repair, scheduling, and multi-format exports."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# ── Custom middleware (order matters – last added = first to run) ─────────────

from app.middleware.audit_logger import AuditLoggerMiddleware
from app.middleware.rate_limiter import InMemoryRateLimiter

app.add_middleware(AuditLoggerMiddleware)
app.add_middleware(InMemoryRateLimiter)

# ── Routers ───────────────────────────────────────────────────────────────────

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.scraping import router as scraping_router
from app.api.routes.ai import router as ai_router
from app.api.routes.sources import router as sources_router
from app.api.routes.exports import router as exports_router
from app.api.routes.logs import router as logs_router

PREFIX = "/api/v1"

app.include_router(health_router)                          # GET /health  (no prefix)
app.include_router(auth_router, prefix=PREFIX)             # /api/v1/auth/...
app.include_router(scraping_router, prefix=PREFIX)         # /api/v1/scrape/...
app.include_router(ai_router, prefix=PREFIX)               # /api/v1/ai/...
app.include_router(sources_router, prefix=PREFIX)          # /api/v1/sources/...
app.include_router(exports_router, prefix=PREFIX)          # /api/v1/exports/...
app.include_router(logs_router, prefix=PREFIX)             # /api/v1/logs/...


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    log.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
