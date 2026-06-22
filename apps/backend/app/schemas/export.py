from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    run_id: UUID
    fields: list[str] | None = Field(
        default=None,
        description="Subset of fields to export; None = all fields",
    )
    flatten: bool = Field(
        default=True,
        description="Flatten nested JSON into columns",
    )
    encoding: str = Field(default="utf-8", pattern="^(utf-8|latin-1|utf-16)$")


class ExportResponse(BaseModel):
    download_url: str
    filename: str
    format: str
    rows: int
    size_bytes: int | None = None
    expires_at: str | None = None
