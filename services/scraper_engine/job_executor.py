"""
JobExecutor — orquestrador principal de execução de scraping.

Decide automaticamente qual engine usar (Scrapy vs Playwright),
gerencia retentativas com backoff exponencial e registra logs por execução.

Fluxo de decisão:
1. Verifica se há API pública disponível (delega ao api_discovery_engine)
2. Detecta se a página é JS-heavy (HEAD request + análise de headers)
3. JS-heavy → PlaywrightRunner
4. Estático → ScrapyRunner
5. Retry automático (até 3x) com backoff exponencial em caso de falha
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .playwright_runner import PlaywrightRunner
from .result_normalizer import ResultNormalizer
from .scrapy_runner import ScrapyRunner

logger = logging.getLogger(__name__)

# Sinais de que a página precisa de JS para renderizar conteúdo útil
_JS_FRAMEWORK_HEADERS = frozenset(["x-nextjs-page", "x-nuxt", "x-gatsby"])
_JS_FRAMEWORKS_BODY = [
    "__NEXT_DATA__",
    "window.__nuxt__",
    "window.__gatsby",
    "ng-version=",
    "data-reactroot",
    "_app.js",
    "bundle.js",
    "chunk.js",
]

# Timeouts e retry config
_DEFAULT_TIMEOUT = 30
_MAX_RETRIES = 3
_BASE_BACKOFF = 2.0  # segundos


class JobExecutor:
    """
    Orquestra a execução de jobs de scraping.

    Parâmetros
    ----------
    api_recommender : optional
        Instância de APIRecommender (api_discovery_engine). Se fornecida,
        verifica APIs públicas antes de scraping.
    force_engine : str, optional
        Força o uso de "scrapy" ou "playwright" independentemente da detecção.
    """

    def __init__(
        self,
        api_recommender: Any = None,
        force_engine: str | None = None,
    ) -> None:
        self.api_recommender = api_recommender
        self.force_engine = force_engine
        self._scrapy = ScrapyRunner()
        self._playwright = PlaywrightRunner()
        self._normalizer = ResultNormalizer()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def execute(self, job: dict) -> dict:
        """
        Executa um job de scraping completo.

        Parâmetros (job dict)
        ---------------------
        url : str (obrigatório)
            URL alvo.
        selectors : dict, optional
            Seletores CSS/XPath por campo.
        engine : str, optional
            "scrapy", "playwright" ou "auto" (padrão).
        timeout : int, optional
            Timeout em segundos (padrão 30).
        search_type : str, optional
            Tipo de busca para recomendação de API ("news", "jobs", etc.).
        job_id : str, optional
            ID externo do job para correlação de logs.
        screenshot : bool, optional
            Captura screenshot (somente Playwright).
        scroll : bool, optional
            Auto-scroll para lazy-load (somente Playwright, padrão True).
        wait_for : str, optional
            Critério de espera do Playwright (padrão "networkidle").

        Retorno
        -------
        dict com:
            job_id, url, engine_used, result (normalizado), api_alternative,
            retries, duration_ms, error (se falhou).
        """
        url = job.get("url", "")
        if not url:
            raise ValueError("JobExecutor.execute(): 'url' é obrigatório no job dict.")

        job_id = job.get("job_id", f"job_{int(time.time() * 1000)}")
        timeout = job.get("timeout", _DEFAULT_TIMEOUT)
        selectors = job.get("selectors")
        search_type = job.get("search_type", "")

        logger.info("JobExecutor.execute() START | job_id=%s | url=%s", job_id, url)
        t0 = time.monotonic()

        execution_log: dict = {
            "job_id": job_id,
            "url": url,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "retries": 0,
            "api_alternative": None,
            "engine_used": None,
            "result": None,
            "error": None,
            "duration_ms": 0,
        }

        # 1. Verifica APIs públicas alternativas
        if self.api_recommender and search_type:
            api_alts = await self._check_apis(url, search_type)
            if api_alts:
                execution_log["api_alternative"] = api_alts
                logger.info(
                    "JobExecutor: APIs disponíveis para '%s': %s",
                    search_type, [a["name"] for a in api_alts],
                )

        # 2. Detecta engine
        engine = self.force_engine or job.get("engine", "auto")
        if engine == "auto":
            engine = await self._detect_engine(url, timeout)

        execution_log["engine_used"] = engine

        # 3. Executa com retry
        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    "JobExecutor: tentativa %d/%d | engine=%s | job_id=%s",
                    attempt, _MAX_RETRIES, engine, job_id,
                )
                raw_result = await self._run_engine(engine, url, job, timeout)
                normalized = self._normalizer.normalize(
                    raw_result if isinstance(raw_result, list) else [raw_result],
                    source_url=url,
                    engine=engine,
                )
                execution_log["result"] = normalized
                execution_log["retries"] = attempt - 1
                break

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "JobExecutor: falha na tentativa %d | job_id=%s | erro: %s",
                    attempt, job_id, exc,
                )
                if attempt < _MAX_RETRIES:
                    backoff = _BASE_BACKOFF ** attempt
                    logger.info("JobExecutor: aguardando %.1fs antes de retry...", backoff)
                    await asyncio.sleep(backoff)
                    # Na segunda tentativa, se Scrapy falhou, tenta Playwright
                    if engine == "scrapy" and attempt == 1:
                        engine = "playwright"
                        execution_log["engine_used"] = engine
                        logger.info("JobExecutor: fallback para Playwright")

        if execution_log["result"] is None:
            execution_log["error"] = str(last_error) if last_error else "Falha desconhecida"
            execution_log["retries"] = _MAX_RETRIES

        execution_log["duration_ms"] = round((time.monotonic() - t0) * 1000, 2)
        execution_log["finished_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "JobExecutor.execute() DONE | job_id=%s | engine=%s | duration=%.0fms | error=%s",
            job_id, execution_log["engine_used"], execution_log["duration_ms"], execution_log["error"],
        )
        return execution_log

    async def execute_batch(self, jobs: list[dict], concurrency: int = 5) -> list[dict]:
        """
        Executa múltiplos jobs em paralelo com limite de concorrência.

        Parâmetros
        ----------
        jobs : list[dict]
            Lista de jobs para executar.
        concurrency : int
            Número máximo de jobs simultâneos (padrão 5).

        Retorno
        -------
        list[dict] com resultados na mesma ordem dos jobs.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(job: dict) -> dict:
            async with semaphore:
                return await self.execute(job)

        tasks = [_bounded(job) for job in jobs]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _detect_engine(self, url: str, timeout: int) -> str:
        """
        Detecta se a página necessita de JS (Playwright) ou não (Scrapy).

        Heurísticas:
        - Headers de frameworks JS no response
        - Corpo HTML contém sinais de SPA (React, Next.js, Vue, Angular)
        - Pouco conteúdo visível no HTML estático (< 500 chars de texto)
        """
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                html = resp.text

            # Verifica headers de frameworks
            for header in _JS_FRAMEWORK_HEADERS:
                if header in resp.headers:
                    logger.info("JobExecutor._detect_engine: JS detectado via header '%s'", header)
                    return "playwright"

            # Verifica sinais no HTML
            for signal in _JS_FRAMEWORKS_BODY:
                if signal in html:
                    logger.info("JobExecutor._detect_engine: JS detectado via sinal '%s'", signal)
                    return "playwright"

            # Heurística de pouco texto visível
            import re
            visible_text = re.sub(r"<[^>]+>", "", html)
            visible_text = re.sub(r"\s+", " ", visible_text).strip()
            if len(visible_text) < 500:
                logger.info(
                    "JobExecutor._detect_engine: pouco texto estático (%d chars), usando Playwright",
                    len(visible_text),
                )
                return "playwright"

            return "scrapy"

        except Exception as exc:
            logger.warning("JobExecutor._detect_engine falhou (%s), usando Scrapy como padrão", exc)
            return "scrapy"

    async def _run_engine(
        self, engine: str, url: str, job: dict, timeout: int
    ) -> list[dict] | dict:
        """Despacha para o runner correto."""
        selectors = job.get("selectors")

        if engine == "playwright":
            return await self._playwright.run(
                url=url,
                selectors=selectors,
                wait_for=job.get("wait_for", "networkidle"),
                timeout=timeout * 1000,  # ms
                stealth=True,
                screenshot=job.get("screenshot", False),
                scroll=job.get("scroll", True),
            )
        else:
            # Scrapy
            return await self._scrapy.run(
                url=url,
                selectors=selectors,
                settings_override={"DOWNLOAD_TIMEOUT": timeout},
            )

    async def _check_apis(self, url: str, search_type: str) -> list[dict]:
        """Consulta o APIRecommender se disponível."""
        try:
            if hasattr(self.api_recommender, "recommend"):
                return await self.api_recommender.recommend(url, search_type)
        except Exception as exc:
            logger.warning("JobExecutor._check_apis falhou: %s", exc)
        return []
