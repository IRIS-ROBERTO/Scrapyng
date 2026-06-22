"""
Health checker — verifica status de todos os serviços da plataforma.
Usado pelo endpoint GET /health.
"""
import asyncio
import httpx
import redis.asyncio as aioredis
import structlog
from datetime import datetime

log = structlog.get_logger()


class HealthChecker:
    def __init__(self, database_url: str, redis_url: str, minio_endpoint: str):
        self.database_url = database_url
        self.redis_url = redis_url
        self.minio_endpoint = minio_endpoint

    async def check_all(self) -> dict:
        results = await asyncio.gather(
            self._check_database(),
            self._check_redis(),
            self._check_minio(),
            self._check_nvidia_api(),
            return_exceptions=True,
        )
        services = {
            "database": results[0] if not isinstance(results[0], Exception) else {"status": "unhealthy", "error": str(results[0])},
            "redis": results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy", "error": str(results[1])},
            "minio": results[2] if not isinstance(results[2], Exception) else {"status": "unhealthy", "error": str(results[2])},
            "nvidia_api": results[3] if not isinstance(results[3], Exception) else {"status": "unhealthy", "error": str(results[3])},
        }
        overall = "healthy" if all(s.get("status") == "healthy" for s in services.values()) else "degraded"
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services,
        }

    async def _check_database(self) -> dict:
        try:
            import asyncpg
            # Parse postgres URL — replace asyncpg:// prefix if needed
            url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncio.wait_for(asyncpg.connect(url), timeout=5.0)
            await conn.execute("SELECT 1")
            await conn.close()
            return {"status": "healthy", "latency_ms": None}
        except Exception as e:
            log.error("health_check_failed", service="database", error=str(e))
            return {"status": "unhealthy", "error": str(e)[:100]}

    async def _check_redis(self) -> dict:
        try:
            client = aioredis.from_url(self.redis_url)
            await asyncio.wait_for(client.ping(), timeout=3.0)
            await client.aclose()
            return {"status": "healthy"}
        except Exception as e:
            log.error("health_check_failed", service="redis", error=str(e))
            return {"status": "unhealthy", "error": str(e)[:100]}

    async def _check_minio(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"http://{self.minio_endpoint}/minio/health/live")
                if resp.status_code == 200:
                    return {"status": "healthy"}
                return {"status": "degraded", "code": resp.status_code}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)[:100]}

    async def _check_nvidia_api(self) -> dict:
        """Verifica conectividade com NVIDIA NIM API (sem consumir tokens)."""
        import os
        api_key = os.environ.get("NVIDIA_API_KEY", "")
        if not api_key:
            return {"status": "not_configured", "message": "NVIDIA_API_KEY não configurada"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://integrate.api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code in (200, 401):
                    # 401 significa auth error mas a API respondeu
                    return {"status": "healthy" if resp.status_code == 200 else "auth_error"}
                return {"status": "degraded", "code": resp.status_code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)[:100]}
