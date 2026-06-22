from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ── Request schemas ───────────────────────────────────────────────────────────

class InstantScrapeRequest(BaseModel):
    url: HttpUrl
    selectors: dict[str, str] | None = Field(
        default=None,
        description="Map of field name → CSS selector or XPath",
        examples=[{"title": "h1", "price": ".price"}],
    )
    use_playwright: bool = False
    user_agent: str | None = None
    timeout: int = Field(default=30, ge=5, le=120)
    proxy: str | None = None
    cookies: dict[str, str] | None = None
    headers: dict[str, str] | None = None


class ScheduledScrapeRequest(InstantScrapeRequest):
    name: str = Field(min_length=1, max_length=255)
    cron_expression: str = Field(
        description="Cron expression e.g. '0 */6 * * *'",
        examples=["0 */6 * * *"],
    )
    timezone: str = "America/Sao_Paulo"
    search_type: str | None = Field(default=None, max_length=50)
    search_params: dict[str, Any] | None = None


class TestSelectorRequest(BaseModel):
    url: HttpUrl
    selector: str
    selector_type: str = Field(default="css", pattern="^(css|xpath)$")
    use_playwright: bool = False


class JobUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(paused|running)$")
    config: dict[str, Any] | None = None


# ── Response schemas ──────────────────────────────────────────────────────────

class ScrapeRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_msg: str | None
    items_count: int | None
    duration_ms: int | None
    created_at: datetime


class ScrapeJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    status: str
    job_type: str
    created_at: datetime
    updated_at: datetime
    last_run: datetime | None = None
    next_run: datetime | None = None
    items_count: int | None = None


class ScrapeJobDetailResponse(ScrapeJobResponse):
    config: dict[str, Any] | None = None
    runs: list[ScrapeRunResponse] = []


class ScrapeResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    raw_data: dict[str, Any] | None
    structured_data: dict[str, Any] | None
    quality_score: float | None
    created_at: datetime


class InstantScrapeResponse(BaseModel):
    job_id: UUID
    run_id: UUID
    status: str
    message: str
    results: list[dict[str, Any]] = []


class TestSelectorResponse(BaseModel):
    matched: bool
    count: int
    samples: list[str]
    error: str | None = None


class PaginatedJobsResponse(BaseModel):
    items: list[ScrapeJobResponse]
    total: int
    page: int
    page_size: int
    pages: int
