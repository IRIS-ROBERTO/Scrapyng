from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.ai import (
    AnalyzePageRequest,
    AnalyzePageResponse,
    GenerateScraperRequest,
    GenerateScraperResponse,
    RepairScraperRequest,
    RepairScraperResponse,
    SuggestedField,
)

router = APIRouter(prefix="/ai", tags=["AI"])
log = get_logger(__name__)


class ModelActionRequest(BaseModel):
    model_id: str


MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "nvidia/nemotron-3-ultra-550b-a55b": {
        "name": "Nemotron 3 Ultra 550B",
        "provider": "NVIDIA",
        "context_length": "256K+",
        "speed": "Media",
        "tier": "frontier",
        "strength": "Raciocinio profundo, agentes complexos, codigo, ciencia e analise longa",
    },
    "deepseek-ai/deepseek-v4-pro": {
        "name": "DeepSeek V4 Pro",
        "provider": "DeepSeek AI",
        "context_length": "1M",
        "speed": "Media",
        "tier": "frontier",
        "strength": "Codigo, agentes, tool use, raciocinio matematico e contexto muito longo",
    },
    "nvidia/nemotron-3-super-120b-a12b": {
        "name": "Nemotron 3 Super 120B",
        "provider": "NVIDIA",
        "context_length": "256K+",
        "speed": "Alta",
        "tier": "premium",
        "strength": "Agentes colaborativos, alto volume e instrucao complexa",
    },
    "deepseek-ai/deepseek-v4-flash": {
        "name": "DeepSeek V4 Flash",
        "provider": "DeepSeek AI",
        "context_length": "1M",
        "speed": "Muito Alta",
        "tier": "premium",
        "strength": "Codigo e agentes com baixa latencia",
    },
    "nvidia/llama-3.3-70b-instruct": {
        "name": "Llama 3.3 70B Instruct",
        "provider": "NVIDIA / Meta",
        "context_length": "128K",
        "speed": "Alta",
        "tier": "fallback",
        "strength": "Modelo geral estavel",
    },
    "meta/llama-3.1-405b-instruct": {
        "name": "Llama 3.1 405B Instruct",
        "provider": "NVIDIA / Meta",
        "context_length": "128K",
        "speed": "Media",
        "tier": "fallback",
        "strength": "Reserva legada de alta capacidade",
    },
    "nvidia/mistral-nemo-12b-instruct": {
        "name": "Mistral Nemo 12B",
        "provider": "NVIDIA / Mistral",
        "context_length": "128K",
        "speed": "Muito Alta",
        "tier": "light_fallback",
        "strength": "Fallback rapido e barato",
    },
    "nvidia/gemma-2-27b-it": {
        "name": "Gemma 2 27B IT",
        "provider": "NVIDIA / Google",
        "context_length": "8K",
        "speed": "Alta",
        "tier": "light_fallback",
        "strength": "Fallback leve para tarefas simples",
    },
    "nvidia/llama-3.1-8b-instruct": {
        "name": "Llama 3.1 8B Instruct",
        "provider": "NVIDIA / Meta",
        "context_length": "128K",
        "speed": "Muito Alta",
        "tier": "last_resort",
        "strength": "Ultimo recurso compacto",
    },
}

_preferred_model: str | None = None


def _ordered_models() -> list[str]:
    models = list(settings.NVIDIA_MODELS)
    if _preferred_model and _preferred_model in models:
        return [_preferred_model] + [model for model in models if model != _preferred_model]
    return models


# ── NVIDIA AI client with model fallback chain ─────────────────────────────────

async def _call_nvidia_ai(
    messages: list[dict],
    *,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> tuple[str, str, int | None]:
    """
    Try each model in the fallback chain.
    Returns (content, model_used, tokens_used).
    Raises HTTPException if all models fail.
    """
    if not settings.NVIDIA_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NVIDIA_API_KEY not configured",
        )

    last_error: str = ""
    for model in _ordered_models():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.NVIDIA_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens")
                    log.info("nvidia_ai_success", model=model, tokens=tokens)
                    return content, model, tokens
                last_error = f"Model {model} returned HTTP {resp.status_code}: {resp.text[:200]}"
                log.warning("nvidia_model_failed", model=model, status=resp.status_code)
        except Exception as exc:
            last_error = str(exc)
            log.warning("nvidia_model_exception", model=model, error=last_error)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"All NVIDIA models failed. Last error: {last_error}",
    )


async def _fetch_page_html(url: str, use_playwright: bool = False) -> str:
    """Fetch page HTML, optionally using Playwright for dynamic content."""
    if not use_playwright:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(url, headers={"User-Agent": "WebScrapy-Bot/1.0"})
            resp.raise_for_status()
            return resp.text

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle")
        html = await page.content()
        await browser.close()
        return html


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(current_user: CurrentUser) -> dict:
    """Return the active NVIDIA model fallback chain."""
    models = []
    for index, model_id in enumerate(_ordered_models(), start=1):
        meta = MODEL_CATALOG.get(model_id, {})
        models.append({
            "id": model_id,
            "name": meta.get("name", model_id),
            "provider": meta.get("provider", "NVIDIA"),
            "context_length": meta.get("context_length", "unknown"),
            "speed": meta.get("speed", "unknown"),
            "tier": meta.get("tier", "fallback"),
            "strength": meta.get("strength", ""),
            "priority": index,
            "is_primary": index == 1,
            "status": "configured",
        })

    return {
        "base_url": settings.NVIDIA_BASE_URL,
        "api_configured": bool(settings.NVIDIA_API_KEY),
        "models": models,
    }


@router.post("/models/test")
async def test_model(payload: ModelActionRequest, current_user: CurrentUser) -> dict:
    """Smoke-test a single NVIDIA model with a tiny completion."""
    if payload.model_id not in settings.NVIDIA_MODELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not configured")
    if not settings.NVIDIA_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NVIDIA_API_KEY not configured",
        )

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{settings.NVIDIA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": payload.model_id,
                    "messages": [{"role": "user", "content": "Respond with exactly: ok"}],
                    "max_tokens": 8,
                    "temperature": 0,
                    "stream": False,
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"NVIDIA model request failed: {type(exc).__name__}",
        ) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA model returned HTTP {resp.status_code}: {resp.text[:200]}",
        )

    return {"model": payload.model_id, "available": True, "latency_ms": latency_ms}


@router.post("/models/preferred")
async def set_preferred_model(payload: ModelActionRequest, current_user: CurrentUser) -> dict:
    """Promote a configured model to the first position for this server process."""
    global _preferred_model
    if payload.model_id not in settings.NVIDIA_MODELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not configured")
    _preferred_model = payload.model_id
    return {"preferred_model": _preferred_model, "models": _ordered_models()}


@router.post("/analyze-page", response_model=AnalyzePageResponse)
async def analyze_page(
    payload: AnalyzePageRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Fetch the page and use NVIDIA AI to suggest extractable fields
    with their CSS selectors.
    """
    url_str = str(payload.url)
    log.info("analyze_page_start", url=url_str, user_id=str(current_user.id))

    try:
        html = await _fetch_page_html(url_str, payload.use_playwright)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not fetch page: {exc}",
        )

    # Truncate HTML to keep prompt reasonable
    html_snippet = html[:8000]

    system_msg = (
        "You are an expert web scraping engineer. "
        "Analyze the provided HTML snippet and identify the most useful data fields to extract. "
        "For each field, provide a CSS selector and an example value. "
        "Respond ONLY with valid JSON in this exact format:\n"
        '{"page_type": "string", "title": "string", "pagination_detected": bool, "dynamic_content": bool, '
        '"fields": [{"name": "str", "css_selector": "str", "xpath_selector": "str", "sample_value": "str", "confidence": 0.0-1.0}]}'
    )

    user_msg = f"URL: {url_str}\n\nHint: {payload.hint or 'general data extraction'}\n\nHTML:\n{html_snippet}"

    content, model_used, tokens = await _call_nvidia_ai(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        max_tokens=1024,
        temperature=0.1,
    )

    # Parse AI response
    import json, re

    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?|```", "", content).strip()
        data: dict[str, Any] = json.loads(clean)
    except json.JSONDecodeError:
        data = {"fields": [], "page_type": "unknown", "pagination_detected": False, "dynamic_content": False, "title": None}

    fields = [SuggestedField(**f) for f in data.get("fields", [])]

    return {
        "url": url_str,
        "title": data.get("title"),
        "suggested_fields": fields,
        "page_type": data.get("page_type"),
        "pagination_detected": data.get("pagination_detected", False),
        "dynamic_content": data.get("dynamic_content", False),
        "model_used": model_used,
        "tokens_used": tokens,
    }


@router.post("/generate-scraper", response_model=GenerateScraperResponse)
async def generate_scraper(
    payload: GenerateScraperRequest,
    current_user: CurrentUser,
) -> dict:
    """Generate a complete spider/scraper script using NVIDIA AI."""
    url_str = str(payload.url)
    log.info("generate_scraper_start", url=url_str, framework=payload.framework, user_id=str(current_user.id))

    fields_desc = "\n".join(f"  - {k}: {v}" for k, v in payload.fields.items())

    if payload.framework == "scrapy":
        system_msg = (
            "You are a senior Scrapy developer. Generate a complete, production-ready Scrapy spider. "
            "Include proper imports, Spider class, start_requests, parse method, and Item class. "
            "Add error handling and respect robots.txt. Output ONLY the Python code, no explanation."
        )
        filename = "spider.py"
    elif payload.framework == "playwright":
        system_msg = (
            "You are a senior Playwright/Python developer. Generate a complete async Playwright script. "
            "Include proper browser setup, page navigation, data extraction, and cleanup. "
            "Output ONLY the Python code, no explanation."
        )
        filename = "scraper_playwright.py"
    else:
        system_msg = (
            "You are a senior Python developer. Generate a complete async httpx + parsel scraper. "
            "Include proper error handling, retries, and data extraction. "
            "Output ONLY the Python code, no explanation."
        )
        filename = "scraper_httpx.py"

    user_msg = (
        f"Generate a {payload.framework} scraper for:\n"
        f"URL: {url_str}\n\n"
        f"Fields to extract:\n{fields_desc}\n\n"
        f"Output format: {payload.output_format}\n"
        "Make it production-ready with error handling."
    )

    content, model_used, tokens = await _call_nvidia_ai(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        max_tokens=2048,
        temperature=0.15,
    )

    # Strip markdown code fences
    import re
    code = re.sub(r"```(?:python)?|```", "", content).strip()

    return {
        "framework": payload.framework,
        "code": code,
        "filename": filename,
        "instructions": (
            f"1. Install requirements: pip install {payload.framework} parsel\n"
            f"2. Run: python {filename}\n"
            "3. Output will be saved as data." + payload.output_format
        ),
        "estimated_speed": "~100-500 req/min depending on site",
        "model_used": model_used,
        "tokens_used": tokens,
    }


@router.post("/repair-scraper", response_model=RepairScraperResponse)
async def repair_scraper(
    payload: RepairScraperRequest,
    current_user: CurrentUser,
) -> dict:
    """Automatically diagnose and repair a broken scraper using NVIDIA AI."""
    url_str = str(payload.url)
    log.info("repair_scraper_start", url=url_str, user_id=str(current_user.id))

    system_msg = (
        "You are an expert web scraping debugger. "
        "Given broken spider code and its error log, identify the root cause and provide a fixed version. "
        "Respond ONLY with valid JSON:\n"
        '{"root_cause": "str", "changes_made": ["str"], "confidence": 0.0-1.0, "repaired_code": "full fixed code"}'
    )

    user_msg = (
        f"Target URL: {url_str}\n"
        f"Expected fields: {', '.join(payload.expected_fields)}\n\n"
        f"ERROR LOG:\n{payload.error_log[:3000]}\n\n"
        f"BROKEN CODE:\n{payload.spider_code[:4000]}\n\n"
        "Fix the code and explain what was wrong."
    )

    content, model_used, tokens = await _call_nvidia_ai(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        max_tokens=2048,
        temperature=0.1,
    )

    import json, re

    try:
        clean = re.sub(r"```(?:json)?|```", "", content).strip()
        data: dict[str, Any] = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: return raw content as repaired code
        data = {
            "root_cause": "Could not parse AI response",
            "changes_made": [],
            "confidence": 0.3,
            "repaired_code": content,
        }

    return {
        "repaired_code": data.get("repaired_code", payload.spider_code),
        "changes_made": data.get("changes_made", []),
        "root_cause": data.get("root_cause", "Unknown"),
        "model_used": model_used,
        "tokens_used": tokens,
        "confidence": float(data.get("confidence", 0.5)),
    }
