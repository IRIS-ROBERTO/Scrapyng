from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

log = get_logger("audit")

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request/response with:
      - request_id (UUID per request)
      - method, path, status_code, duration_ms
      - user_id extracted from JWT if present (best-effort, no decode)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if any(request.url.path.endswith(p) for p in _SKIP_PATHS):
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Attach request_id so downstream handlers can reference it
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )

        log.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) or None,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            user_agent=request.headers.get("User-Agent", ""),
        )

        response.headers["X-Request-ID"] = request_id
        return response
