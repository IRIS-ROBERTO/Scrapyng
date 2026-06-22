"""
NVIDIA NIM API client with automatic fallback chain between models.

If a model fails (timeout, 429, 503, etc.) the client transparently
tries the next model in the NVIDIA_MODELS_FALLBACK list.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Fallback model chain — ordered by preference
# ---------------------------------------------------------------------------
NVIDIA_MODELS_FALLBACK: list[str] = [
    "nvidia/nemotron-3-ultra-550b-a55b",    # Primary: frontier reasoning/agents
    "deepseek-ai/deepseek-v4-pro",          # Fallback 1: 1M context, coding/reasoning
    "nvidia/nemotron-3-super-120b-a12b",    # Fallback 2: strong high-volume agent model
    "deepseek-ai/deepseek-v4-flash",        # Fallback 3: fast MoE coding/agents
    "nvidia/llama-3.3-70b-instruct",        # Fallback 4: stable general model
    "meta/llama-3.1-405b-instruct",         # Fallback 5: legacy high-capability reserve
    "nvidia/mistral-nemo-12b-instruct",     # Fallback 6: fast/light
    "nvidia/gemma-2-27b-it",                # Fallback 7: light
    "nvidia/llama-3.1-8b-instruct",         # Fallback 8: compact last resort
]

# Errors that should trigger a fallback to the next model
_RETRIABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class NvidiaClientError(Exception):
    """Raised when all models in the fallback chain have been exhausted."""


class NvidiaClient:
    """
    Async NVIDIA NIM client with automatic model fallback.

    Usage::

        client = NvidiaClient(api_key=os.environ["NVIDIA_API_KEY"])
        text = await client.chat([{"role": "user", "content": "Hello"}])
        data = await client.chat_json([{"role": "user", "content": "Return JSON…"}])
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        models: list[str] | None = None,
        retry_delay: float = 0.5,
        request_timeout: float = 60.0,
    ) -> None:
        self.api_key: str = api_key or os.environ["NVIDIA_API_KEY"]
        self.base_url: str = base_url.rstrip("/")
        self.models: list[str] = models if models is not None else list(NVIDIA_MODELS_FALLBACK)
        self.retry_delay: float = retry_delay
        self.request_timeout: float = request_timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.1,
        system_prompt: str | None = None,
    ) -> str:
        """
        Send a chat completion request with automatic model fallback.

        Parameters
        ----------
        messages:
            List of ``{"role": ..., "content": ...}`` dicts.
        max_tokens:
            Maximum tokens in the completion.
        temperature:
            Sampling temperature (lower = more deterministic).
        system_prompt:
            If provided, prepended as a ``system`` message.

        Returns
        -------
        str
            The model's text response.

        Raises
        ------
        NvidiaClientError
            When every model in the chain fails.
        """
        full_messages = self._build_messages(messages, system_prompt)
        last_error: Exception | None = None

        for model in self.models:
            try:
                log.info("nvidia_api_attempt", model=model)
                result = await self._call_model(
                    model=model,
                    messages=full_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                log.info("nvidia_api_success", model=model, response_len=len(result))
                return result
            except Exception as exc:
                log.warning(
                    "nvidia_api_fallback",
                    model=model,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                last_error = exc
                await asyncio.sleep(self.retry_delay)

        raise NvidiaClientError(
            f"All NVIDIA models failed. Last error: {last_error}"
        ) from last_error

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Send a chat request and parse the response as JSON.

        Strips markdown code fences (```json … ```) automatically.

        Returns
        -------
        dict
            Parsed JSON object.

        Raises
        ------
        NvidiaClientError
            When all models fail.
        json.JSONDecodeError
            When the response cannot be parsed as JSON even after cleanup.
        """
        text = await self.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.05,   # low temperature for deterministic JSON
            max_tokens=max_tokens,
        )
        return self._parse_json(text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        messages: list[dict[str, str]],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + list(messages)
        return list(messages)

    async def _call_model(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Make a single HTTP request to the NVIDIA NIM endpoint."""
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

            if response.status_code in _RETRIABLE_STATUS_CODES:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code} — retriable",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()
            data: dict[str, Any] = response.json()

            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as exc:
                raise NvidiaClientError(
                    f"Unexpected response structure from {model}: {data}"
                ) from exc

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Strip markdown fences and parse JSON."""
        cleaned = text.strip()

        # Remove opening fence  ```json  or  ```
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Drop first line (the fence) and last line if it is also a fence
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            cleaned = "\n".join(lines).strip()

        # Some models wrap with single backtick
        cleaned = cleaned.strip("`").strip()

        return json.loads(cleaned)
