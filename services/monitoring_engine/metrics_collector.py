"""
Coleta e agrega métricas de execução da plataforma.
Armazena em Redis para leitura pelo dashboard.
"""
import json
import time
from datetime import datetime, timedelta
from typing import Any
import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()


class MetricsCollector:
    KEYS = {
        "total_jobs": "metrics:total_jobs",
        "successful_runs": "metrics:successful_runs",
        "failed_runs": "metrics:failed_runs",
        "ai_calls": "metrics:ai_calls",
        "ai_cost_estimate": "metrics:ai_cost_usd",
        "bytes_collected": "metrics:bytes_collected",
        "avg_duration_ms": "metrics:avg_duration_ms",
    }

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if not self._client:
            self._client = await aioredis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def record_job_created(self) -> None:
        client = await self._get_client()
        await client.incr(self.KEYS["total_jobs"])
        log.info("metric_recorded", event="job_created")

    async def record_run_completed(self, duration_ms: int, items_count: int, success: bool) -> None:
        client = await self._get_client()
        pipe = client.pipeline()
        key = self.KEYS["successful_runs"] if success else self.KEYS["failed_runs"]
        pipe.incr(key)
        pipe.incrby(self.KEYS["bytes_collected"], items_count * 512)  # rough estimate
        # Running average for duration
        pipe.lpush("metrics:durations", duration_ms)
        pipe.ltrim("metrics:durations", 0, 999)  # keep last 1000
        await pipe.execute()
        log.info("metric_recorded", event="run_completed", success=success, duration_ms=duration_ms)

    async def record_ai_call(self, model: str, tokens_used: int = 0) -> None:
        client = await self._get_client()
        pipe = client.pipeline()
        pipe.incr(self.KEYS["ai_calls"])
        # Estimate cost: ~$0.001 per 1k tokens (rough NVIDIA NIM estimate)
        cost = (tokens_used / 1000) * 0.001
        pipe.incrbyfloat(self.KEYS["ai_cost_estimate"], cost)
        pipe.incr(f"metrics:model_usage:{model}")
        await pipe.execute()

    async def get_summary(self) -> dict[str, Any]:
        client = await self._get_client()
        pipe = client.pipeline()
        for key in self.KEYS.values():
            pipe.get(key)
        # Also get hourly scrape volume for chart
        for i in range(24):
            hour = (datetime.utcnow() - timedelta(hours=i)).strftime("%Y-%m-%dT%H")
            pipe.get(f"metrics:hourly:{hour}")

        results = await pipe.execute()
        base = dict(zip(self.KEYS.keys(), results[:len(self.KEYS)]))
        hourly_raw = results[len(self.KEYS):]

        # Parse numerics safely
        summary: dict[str, Any] = {
            k: int(v or 0) if k != "ai_cost_estimate" else float(v or 0.0)
            for k, v in base.items()
        }
        summary["success_rate"] = (
            round(
                summary["successful_runs"] / (summary["successful_runs"] + summary["failed_runs"]) * 100, 1
            )
            if (summary["successful_runs"] + summary["failed_runs"]) > 0
            else 0.0
        )
        summary["hourly_volume"] = [int(v or 0) for v in hourly_raw]
        return summary

    async def record_hourly_scrape(self, count: int = 1) -> None:
        client = await self._get_client()
        hour_key = f"metrics:hourly:{datetime.utcnow().strftime('%Y-%m-%dT%H')}"
        pipe = client.pipeline()
        pipe.incrby(hour_key, count)
        pipe.expire(hour_key, 60 * 60 * 48)  # keep 48h
        await pipe.execute()
