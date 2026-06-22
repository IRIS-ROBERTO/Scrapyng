from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.core.logging import get_logger
from app.models.scraping_job import JobStatus, JobType, ScrapingJob
from app.models.scraping_result import ScrapingResult
from app.models.scraping_run import RunStatus, ScrapingRun
from app.models.scraping_schedule import ScrapingSchedule
from app.schemas.scraping import (
    InstantScrapeRequest,
    InstantScrapeResponse,
    JobUpdateRequest,
    PaginatedJobsResponse,
    ScheduledScrapeRequest,
    ScrapeJobDetailResponse,
    ScrapeJobResponse,
    ScrapeResultResponse,
    TestSelectorRequest,
    TestSelectorResponse,
)

router = APIRouter(prefix="/scrape", tags=["Scraping"])
log = get_logger(__name__)


# ── Helper: compute next_run from cron expression ─────────────────────────────
def _compute_next_run(cron_expression: str, tz: str) -> datetime | None:
    try:
        from croniter import croniter
        import pytz

        tz_obj = pytz.timezone(tz)
        now = datetime.now(tz_obj)
        cron = croniter(cron_expression, now)
        return cron.get_next(datetime)
    except Exception:
        return None


# ── Helper: run scrape synchronously (lightweight, no Celery dependency) ──────
async def _execute_scrape(
    job: ScrapingJob,
    run: ScrapingRun,
    db: Any,
) -> None:
    """Execute a scrape and persist results. Called in background."""
    from datetime import datetime, timezone
    import json

    run.status = RunStatus.running
    run.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        config = job.config or {}
        url = job.url
        selectors: dict[str, str] = config.get("selectors") or {}
        use_playwright: bool = config.get("use_playwright", False)
        timeout: int = config.get("timeout", 30)
        headers: dict = config.get("headers") or {}
        cookies: dict = config.get("cookies") or {}
        user_agent = config.get("user_agent", "WebScrapy-Bot/1.0")

        if not use_playwright:
            # httpx-based lightweight scraper
            from parsel import Selector as ParselSelector

            default_headers = {"User-Agent": user_agent, **headers}
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
                headers=default_headers,
                cookies=cookies,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            sel = ParselSelector(html)
            extracted: dict[str, Any] = {}
            for field, css in selectors.items():
                if css.startswith("//"):
                    values = sel.xpath(css).getall()
                else:
                    values = sel.css(css).getall()
                extracted[field] = values[0] if len(values) == 1 else values

            raw = {"html_length": len(html), "url": url, "selectors_used": selectors}
            result = ScrapingResult(
                run_id=run.id,
                raw_data=raw,
                structured_data=extracted,
                quality_score=_score(extracted),
            )
        else:
            # Playwright path
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent=user_agent,
                    extra_http_headers=headers,
                )
                await page.goto(url, timeout=timeout * 1000)
                await page.wait_for_load_state("networkidle")
                html = await page.content()

                extracted = {}
                for field, css in selectors.items():
                    try:
                        elements = await page.query_selector_all(css)
                        texts = [await el.inner_text() for el in elements]
                        extracted[field] = texts[0] if len(texts) == 1 else texts
                    except Exception:
                        extracted[field] = None

                await browser.close()

            raw = {"html_length": len(html), "url": url, "selectors_used": selectors}
            result = ScrapingResult(
                run_id=run.id,
                raw_data=raw,
                structured_data=extracted,
                quality_score=_score(extracted),
            )

        db.add(result)

        run.status = RunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.items_count = 1
        run.duration_ms = int(
            (run.completed_at - run.started_at).total_seconds() * 1000
        )

        job.status = JobStatus.completed
        await db.flush()
        log.info("scrape_completed", job_id=str(job.id), run_id=str(run.id))

    except Exception as exc:
        run.status = RunStatus.failed
        run.error_msg = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        job.status = JobStatus.failed
        await db.flush()
        log.error("scrape_failed", job_id=str(job.id), run_id=str(run.id), error=str(exc))


def _score(data: dict) -> float:
    """Naive quality score: fraction of non-empty fields."""
    if not data:
        return 0.0
    filled = sum(1 for v in data.values() if v)
    return round(filled / len(data), 2)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/instant", response_model=InstantScrapeResponse, status_code=status.HTTP_202_ACCEPTED)
async def instant_scrape(
    payload: InstantScrapeRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """Create a scraping job and immediately dispatch it in the background."""
    url_str = str(payload.url)
    job = ScrapingJob(
        name=f"instant-{url_str[:50]}",
        url=url_str,
        job_type=JobType.instant,
        status=JobStatus.running,
        user_id=current_user.id,
        config={
            "selectors": payload.selectors,
            "use_playwright": payload.use_playwright,
            "user_agent": payload.user_agent,
            "timeout": payload.timeout,
            "headers": payload.headers,
            "cookies": payload.cookies,
        },
    )
    db.add(job)
    await db.flush()

    run = ScrapingRun(job_id=job.id, status=RunStatus.pending)
    db.add(run)
    await db.flush()
    await db.refresh(job)
    await db.refresh(run)

    log.info("instant_scrape_dispatched", job_id=str(job.id), url=url_str)
    background_tasks.add_task(_execute_scrape, job, run, db)

    return {
        "job_id": job.id,
        "run_id": run.id,
        "status": "accepted",
        "message": "Scraping job dispatched. Poll /scrape/jobs/{id} for status.",
        "results": [],
    }


@router.post("/scheduled", response_model=ScrapeJobResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_scrape(
    payload: ScheduledScrapeRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ScrapingJob:
    """Create a recurring scraping job with a cron schedule."""
    url_str = str(payload.url)
    next_run = _compute_next_run(payload.cron_expression, payload.timezone)

    job = ScrapingJob(
        name=payload.name,
        url=url_str,
        job_type=JobType.scheduled,
        status=JobStatus.pending,
        user_id=current_user.id,
        config={
            "selectors": payload.selectors,
            "use_playwright": payload.use_playwright,
            "user_agent": payload.user_agent,
            "timeout": payload.timeout,
            "headers": payload.headers,
            "cookies": payload.cookies,
            "search_type": payload.search_type,
            "search_params": payload.search_params or {},
        },
    )
    db.add(job)
    await db.flush()

    schedule = ScrapingSchedule(
        job_id=job.id,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        next_run=next_run,
        is_active=True,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(job)

    log.info(
        "scheduled_scrape_created",
        job_id=str(job.id),
        cron=payload.cron_expression,
        next_run=str(next_run),
    )
    # Enrich response with schedule info
    job_dict = job.to_dict()
    job_dict["next_run"] = next_run
    job_dict["last_run"] = None
    job_dict["items_count"] = None
    return job_dict


@router.get("/jobs", response_model=PaginatedJobsResponse)
async def list_jobs(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = Query(default=None),
) -> dict:
    """List all scraping jobs for the current user."""
    query = select(ScrapingJob).where(ScrapingJob.user_id == current_user.id)
    if status_filter:
        query = query.where(ScrapingJob.status == status_filter)
    if job_type:
        query = query.where(ScrapingJob.job_type == job_type)

    count_q = select(func.count()).select_from(
        query.subquery()
    )
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(ScrapingJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "items": jobs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/jobs/{job_id}", response_model=ScrapeJobDetailResponse)
async def get_job(
    job_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> ScrapingJob:
    """Get detailed information about a specific job including its runs."""
    result = await db.execute(
        select(ScrapingJob)
        .options(selectinload(ScrapingJob.runs))
        .where(ScrapingJob.id == job_id, ScrapingJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=ScrapeJobResponse)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ScrapingJob:
    """Update a job's name or status (pause/resume)."""
    result = await db.execute(
        select(ScrapingJob).where(ScrapingJob.id == job_id, ScrapingJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if payload.name is not None:
        job.name = payload.name
    if payload.status is not None:
        job.status = payload.status
    if payload.config is not None:
        job.config = {**(job.config or {}), **payload.config}

    await db.flush()
    await db.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_job(
    job_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    """Delete a job and all its runs/results."""
    result = await db.execute(
        select(ScrapingJob).where(ScrapingJob.id == job_id, ScrapingJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    await db.delete(job)
    log.info("job_deleted", job_id=str(job_id))


@router.get("/results/{run_id}", response_model=list[ScrapeResultResponse])
async def get_results(
    run_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> list[ScrapingResult]:
    """Fetch all scraped results for a specific run."""
    # Verify ownership via join
    run_result = await db.execute(
        select(ScrapingRun)
        .join(ScrapingJob, ScrapingRun.job_id == ScrapingJob.id)
        .where(ScrapingRun.id == run_id, ScrapingJob.user_id == current_user.id)
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    results_q = await db.execute(
        select(ScrapingResult).where(ScrapingResult.run_id == run_id)
    )
    return results_q.scalars().all()


@router.post("/test-selector", response_model=TestSelectorResponse)
async def test_selector(payload: TestSelectorRequest) -> dict:
    """Test a CSS or XPath selector against a live URL (no auth required by design)."""
    url_str = str(payload.url)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url_str, headers={"User-Agent": "WebScrapy-Bot/1.0"})
            resp.raise_for_status()
            html = resp.text

        from parsel import Selector as ParselSelector

        sel = ParselSelector(html)
        if payload.selector_type == "xpath" or payload.selector.startswith("//"):
            matches = sel.xpath(payload.selector).getall()
        else:
            matches = sel.css(payload.selector).getall()

        samples = [m[:200] for m in matches[:5]]
        return {"matched": bool(matches), "count": len(matches), "samples": samples}
    except Exception as exc:
        return {"matched": False, "count": 0, "samples": [], "error": str(exc)}
