from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.core.logging import get_logger
from app.models.scraping_result import ScrapingResult
from app.models.scraping_run import ScrapingRun
from app.models.scraping_job import ScrapingJob
from app.schemas.export import ExportRequest, ExportResponse

router = APIRouter(prefix="/exports", tags=["Exports"])
log = get_logger(__name__)


async def _get_results_for_export(
    run_id: uuid.UUID, user_id: uuid.UUID, db: Any
) -> list[dict]:
    """Fetch and verify ownership of results for export."""
    run_q = await db.execute(
        select(ScrapingRun)
        .join(ScrapingJob, ScrapingRun.job_id == ScrapingJob.id)
        .where(ScrapingRun.id == run_id, ScrapingJob.user_id == user_id)
    )
    run = run_q.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found or access denied")

    results_q = await db.execute(
        select(ScrapingResult).where(ScrapingResult.run_id == run_id)
    )
    results = results_q.scalars().all()
    return [r.structured_data or r.raw_data or {} for r in results]


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Recursively flatten a nested dict."""
    items: list = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@router.post("/csv", summary="Export results as CSV")
async def export_csv(
    payload: ExportRequest, current_user: CurrentUser, db: DBSession
) -> StreamingResponse:
    """Stream results as a UTF-8 CSV file."""
    import csv

    rows = await _get_results_for_export(payload.run_id, current_user.id, db)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No results found for this run")

    if payload.flatten:
        rows = [_flatten_dict(r) for r in rows]

    if payload.fields:
        rows = [{k: v for k, v in r.items() if k in payload.fields} for r in rows]

    # Gather all headers
    all_keys: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    csv_bytes = output.getvalue().encode(payload.encoding)

    filename = f"webscrapy_export_{payload.run_id}.csv"
    log.info("export_csv", run_id=str(payload.run_id), rows=len(rows))

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/excel", summary="Export results as Excel (.xlsx)")
async def export_excel(
    payload: ExportRequest, current_user: CurrentUser, db: DBSession
) -> StreamingResponse:
    """Stream results as an Excel workbook."""
    import pandas as pd

    rows = await _get_results_for_export(payload.run_id, current_user.id, db)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No results found for this run")

    if payload.flatten:
        rows = [_flatten_dict(r) for r in rows]

    if payload.fields:
        rows = [{k: v for k, v in r.items() if k in payload.fields} for r in rows]

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    output.seek(0)

    filename = f"webscrapy_export_{payload.run_id}.xlsx"
    log.info("export_excel", run_id=str(payload.run_id), rows=len(rows))

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/json", summary="Export results as JSON")
async def export_json(
    payload: ExportRequest, current_user: CurrentUser, db: DBSession
) -> StreamingResponse:
    """Stream results as a pretty-printed JSON file."""
    rows = await _get_results_for_export(payload.run_id, current_user.id, db)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No results found for this run")

    if payload.fields:
        rows = [{k: v for k, v in r.items() if k in payload.fields} for r in rows]

    json_bytes = json.dumps(
        {"run_id": str(payload.run_id), "count": len(rows), "results": rows},
        indent=2,
        ensure_ascii=False,
        default=str,
    ).encode(payload.encoding)

    filename = f"webscrapy_export_{payload.run_id}.json"
    log.info("export_json", run_id=str(payload.run_id), rows=len(rows))

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
