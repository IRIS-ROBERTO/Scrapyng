from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://webscrapy:webscrapy@postgres:5432/webscrapy"

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── NVIDIA AI – fallback chain ─────────────────────────────────────────
    NVIDIA_API_KEY: str = ""          # NEVER hard-code; must come from env
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODELS: List[str] = [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "deepseek-ai/deepseek-v4-pro",
        "nvidia/nemotron-3-super-120b-a12b",
        "deepseek-ai/deepseek-v4-flash",
        "nvidia/llama-3.3-70b-instruct",
        "meta/llama-3.1-405b-instruct",
        "nvidia/mistral-nemo-12b-instruct",
        "nvidia/gemma-2-27b-it",
        "nvidia/llama-3.1-8b-instruct",
    ]

    # ── JWT ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── MinIO ─────────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "webscrapy-results"

    # ── Celery ────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ── Application ───────────────────────────────────────────────────────
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.NVIDIA_API_KEY:
        settings.NVIDIA_API_KEY = os.getenv("NVIDIA_API", "").strip()
    return settings


settings = get_settings()
