from __future__ import annotations

from fastapi import APIRouter

from app.core.redis_client import ping_redis
from app.core.logging import get_logger

router = APIRouter(tags=["Health"])
log = get_logger(__name__)


@router.get("/health", summary="System health check")
async def health_check() -> dict:
    """Public endpoint – no auth required. Returns status of all services."""
    redis_ok = await ping_redis()

    # Lightweight DB check
    db_ok = False
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        log.warning("db_health_check_failed", error=str(exc))

    overall = "ok" if (redis_ok and db_ok) else "degraded"

    return {
        "status": overall,
        "services": {
            "database": "ok" if db_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
        "version": "1.0.0",
    }
