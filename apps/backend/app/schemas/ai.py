from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# ── Request schemas ───────────────────────────────────────────────────────────

class AnalyzePageRequest(BaseModel):
    url: HttpUrl
    use_playwright: bool = False
    hint: str | None = Field(
        default=None,
        description="Optional hint about what data to extract",
        examples=["product listings", "news articles"],
    )


class GenerateScraperRequest(BaseModel):
    url: HttpUrl
    fields: dict[str, str] = Field(
        description="Map of field name → description",
        examples=[{"title": "product title", "price": "product price in BRL"}],
    )
    framework: str = Field(default="scrapy", pattern="^(scrapy|playwright|httpx)$")
    output_format: str = Field(default="json", pattern="^(json|csv|jsonl)$")


class RepairScraperRequest(BaseModel):
    spider_code: str = Field(description="Current spider/scraper source code")
    error_log: str = Field(description="Error output from the last run")
    url: HttpUrl
    expected_fields: list[str] = Field(default_factory=list)


# ── Response schemas ──────────────────────────────────────────────────────────

class SuggestedField(BaseModel):
    name: str
    css_selector: str | None = None
    xpath_selector: str | None = None
    sample_value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class AnalyzePageResponse(BaseModel):
    url: str
    title: str | None
    suggested_fields: list[SuggestedField]
    page_type: str | None = None
    pagination_detected: bool = False
    dynamic_content: bool = False
    model_used: str
    tokens_used: int | None = None


class GenerateScraperResponse(BaseModel):
    framework: str
    code: str
    filename: str
    instructions: str
    estimated_speed: str | None = None
    model_used: str
    tokens_used: int | None = None


class RepairScraperResponse(BaseModel):
    repaired_code: str
    changes_made: list[str]
    root_cause: str
    model_used: str
    tokens_used: int | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class AIModelStatus(BaseModel):
    model: str
    available: bool
    latency_ms: int | None = None
