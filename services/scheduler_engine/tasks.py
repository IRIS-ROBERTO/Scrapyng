"""
Tasks Celery para execução de jobs de scraping.

Todas as tasks são idempotentes e possuem retry com backoff exponencial.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from celery import states
from celery.exceptions import MaxRetriesExceededError

from .celery_app import app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_job_manager():
    """Lazy import para evitar dependência circular."""
    from .job_manager import JobManager
    return JobManager()


def _get_job_executor():
    """Lazy import do JobExecutor."""
    from services.scraper_engine.job_executor import JobExecutor
    return JobExecutor()


def _run_async(coro):
    """Executa coroutine em event loop compatível com Celery (thread worker)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Task principal de scraping
# ---------------------------------------------------------------------------

@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="services.scheduler_engine.tasks.execute_scraping_job",
    acks_late=True,
    track_started=True,
)
def execute_scraping_job(self, job_id: str) -> dict:
    """
    Task principal: carrega o job do banco, executa o scraping e salva o resultado.

    Parâmetros
    ----------
    job_id : str
        ID do job a ser executado.

    Retorno
    -------
    dict com resultado da execução ou erro.
    """
    logger.info("execute_scraping_job | START | job_id=%s | attempt=%d", job_id, self.request.retries + 1)
    t0 = time.monotonic()

    job_manager = _get_job_manager()
    executor = _get_job_executor()

    # Carrega job
    job = job_manager.get(job_id)
    if not job:
        logger.error("execute_scraping_job | job_id=%s não encontrado", job_id)
        return {"error": f"Job {job_id} não encontrado", "job_id": job_id}

    # Marca como em execução
    job_manager.update_status(job_id, status="running", celery_task_id=self.request.id)

    try:
        # Executa com backoff exponencial via retry do Celery
        result = _run_async(executor.execute(job))

        duration_ms = round((time.monotonic() - t0) * 1000, 2)
        result["duration_ms"] = duration_ms

        if result.get("error"):
            logger.warning(
                "execute_scraping_job | PARTIAL_FAIL | job_id=%s | erro=%s",
                job_id, result["error"],
            )
            job_manager.update_status(
                job_id,
                status="failed",
                error=result["error"],
                result=result,
                duration_ms=duration_ms,
            )
        else:
            logger.info(
                "execute_scraping_job | SUCCESS | job_id=%s | duration=%.0fms",
                job_id, duration_ms,
            )
            job_manager.update_status(
                job_id,
                status="completed",
                result=result,
                duration_ms=duration_ms,
            )

        # Se job é recorrente, agenda próxima execução
        if job.get("schedule"):
            _schedule_next_run(job_manager, job_id, job)

        return result

    except Exception as exc:
        duration_ms = round((time.monotonic() - t0) * 1000, 2)
        logger.exception(
            "execute_scraping_job | ERROR | job_id=%s | attempt=%d | erro=%s",
            job_id, self.request.retries + 1, exc,
        )
        job_manager.update_status(
            job_id,
            status="retrying" if self.request.retries < self.max_retries else "failed",
            error=str(exc),
            duration_ms=duration_ms,
        )

        try:
            # Backoff exponencial: 60s, 120s, 240s
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(
                "execute_scraping_job | MAX_RETRIES | job_id=%s | desistindo.", job_id
            )
            job_manager.update_status(job_id, status="failed", error=str(exc))
            return {"error": str(exc), "job_id": job_id, "status": "failed"}


# ---------------------------------------------------------------------------
# Task de verificação de jobs agendados
# ---------------------------------------------------------------------------

@app.task(
    name="services.scheduler_engine.tasks.check_and_trigger_scheduled_jobs",
    ignore_result=True,
)
def check_and_trigger_scheduled_jobs() -> None:
    """
    Verifica jobs agendados com 'next_run' <= agora e dispara execução.
    Executada pelo celery-beat a cada minuto.
    """
    logger.debug("check_and_trigger_scheduled_jobs | verificando jobs agendados...")
    job_manager = _get_job_manager()
    now = datetime.now(timezone.utc)

    due_jobs = job_manager.get_due_jobs(now)
    if not due_jobs:
        return

    logger.info("check_and_trigger_scheduled_jobs | %d jobs prontos para execução", len(due_jobs))

    for job in due_jobs:
        job_id = job["job_id"]
        try:
            # Dispara a task de scraping
            task_result = execute_scraping_job.apply_async(
                args=[job_id],
                queue="scraping",
                task_id=f"{job_id}_{int(time.time())}",
            )
            logger.info(
                "check_and_trigger_scheduled_jobs | disparado job_id=%s | celery_task=%s",
                job_id, task_result.id,
            )
            job_manager.update_status(job_id, status="queued", celery_task_id=task_result.id)
        except Exception as exc:
            logger.error(
                "check_and_trigger_scheduled_jobs | falha ao disparar job_id=%s: %s",
                job_id, exc,
            )


# ---------------------------------------------------------------------------
# Task de limpeza
# ---------------------------------------------------------------------------

@app.task(
    name="services.scheduler_engine.tasks.cleanup_old_results",
    ignore_result=True,
)
def cleanup_old_results(days: int = 30) -> None:
    """
    Remove resultados de jobs mais antigos que `days` dias.
    Executada diariamente pelo celery-beat.
    """
    logger.info("cleanup_old_results | removendo resultados com mais de %d dias", days)
    job_manager = _get_job_manager()
    removed = job_manager.cleanup_old(days=days)
    logger.info("cleanup_old_results | removidos=%d registros", removed)


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------

def _schedule_next_run(job_manager: Any, job_id: str, job: dict) -> None:
    """Agenda próxima execução para jobs recorrentes."""
    from .scheduler import compute_next_run
    next_run = compute_next_run(job.get("schedule", ""))
    if next_run:
        job_manager.set_next_run(job_id, next_run)
        logger.info(
            "_schedule_next_run | job_id=%s | próxima_execução=%s",
            job_id, next_run.isoformat(),
        )
