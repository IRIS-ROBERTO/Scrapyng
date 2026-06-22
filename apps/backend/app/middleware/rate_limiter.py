from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class InMemoryRateLimiter(BaseHTTPMiddleware):
    """
    Simple sliding-window in-process rate limiter.

    For multi-process deployments swap the `_requests` dict for a Redis
    sorted set (see redis_client.py) – the logic stays the same.
    """

    # { client_key: [timestamp, timestamp, ...] }
    _requests: dict[str, list[float]] = defaultdict(list)

    def __init__(
        self,
        app,
        *,
        requests_per_minute: int | None = None,
        # Public paths that are exempt from rate limiting
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.window = 60.0
        self.exempt = set(exempt_paths or ["/api/v1/health", "/docs", "/openapi.json", "/redoc"])

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
        return ip

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exempt:
            return await call_next(request)

        key = self._get_client_key(request)
        now = time.monotonic()
        window_start = now - self.window

        # Slide the window
        timestamps = self._requests[key]
        # Remove timestamps outside the window
        while timestamps and timestamps[0] < window_start:
            timestamps.pop(0)

        if len(timestamps) >= self.rpm:
            log.warning("rate_limit_exceeded", client=key, path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Try again in a minute.",
                    "retry_after": int(self.window - (now - timestamps[0])),
                },
                headers={"Retry-After": str(int(self.window - (now - timestamps[0])))},
            )

        timestamps.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - len(timestamps)))
        return response
