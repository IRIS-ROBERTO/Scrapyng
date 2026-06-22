from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
    return _pool


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.Redis(connection_pool=get_redis_pool())
    return _client


async def close_redis() -> None:
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def ping_redis() -> bool:
    try:
        client = get_redis()
        return await client.ping()
    except Exception:
        return False
