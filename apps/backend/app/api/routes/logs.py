from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.scraping_job import ScrapingJob
from app.models.scraping_run import ScrapingRun

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("", summary="Get run logs for the current user")
async def get_logs(
    current_user: CurrentUser,
    db: DBSession,
    job_id: uuid.UUID | None = Query(default=None, description="Filter by job ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Return paginated run history with status, duration, and error details."""
    query = (
        select(ScrapingRun)
        .join(ScrapingJob, ScrapingRun.job_id == ScrapingJob.id)
        .where(ScrapingJob.user_id == current_user.id)
    )

    if job_id:
        query = query.where(ScrapingRun.job_id == job_id)

    query = query.order_by(ScrapingRun.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    log_entries = [
        {
            "run_id": str(r.id),
            "job_id": str(r.job_id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_ms": r.duration_ms,
            "items_count": r.items_count,
            "error_msg": r.error_msg,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]

    return {
        "page": page,
        "page_size": page_size,
        "count": len(log_entries),
        "entries": log_entries,
    }
