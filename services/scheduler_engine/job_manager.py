"""
JobManager — CRUD de jobs agendados persistido em SQLite.

Gerencia o ciclo de vida completo dos jobs:
- Criação com validação
- Consulta por ID, status, próxima execução
- Atualização de status e resultados
- Listagem e filtragem
- Limpeza de jobs antigos
"""

import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .scheduler import compute_next_run, validate_schedule

logger = logging.getLogger(__name__)

_DEFAULT_DB = os.environ.get("JOBS_DB_PATH", "/tmp/webscrapy_jobs.db")

# Status válidos
STATUS_PENDING = "pending"
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES = {
    STATUS_PENDING, STATUS_QUEUED, STATUS_RUNNING,
    STATUS_COMPLETED, STATUS_FAILED, STATUS_RETRYING, STATUS_CANCELLED,
}


class JobManager:
    """
    Gerencia jobs de scraping em banco SQLite.

    Exemplo de uso
    --------------
    jm = JobManager()

    job_id = jm.create({
        "url": "https://exemplo.com",
        "selectors": {"titulo": "h1::text"},
        "engine": "auto",
        "schedule": "every_1h",
    })

    jm.update_status(job_id, status="running")
    job = jm.get(job_id)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _DEFAULT_DB
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, job_data: dict) -> str:
        """
        Cria um novo job.

        Parâmetros obrigatórios em job_data:
            url : str

        Parâmetros opcionais:
            selectors : dict
            engine : str (auto|scrapy|playwright)
            schedule : str (every_1h, cron, ISO8601)
            timeout : int (segundos, padrão 30)
            search_type : str
            tags : list[str]
            wait_for : str
            screenshot : bool
            scroll : bool

        Retorno
        -------
        str : job_id gerado (UUID4)
        """
        url = job_data.get("url", "").strip()
        if not url:
            raise ValueError("JobManager.create(): 'url' é obrigatório.")

        schedule = job_data.get("schedule", "")
        valid, err = validate_schedule(schedule)
        if not valid:
            raise ValueError(f"JobManager.create(): schedule inválido — {err}")

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        next_run = compute_next_run(schedule) if schedule else None

        record = {
            "job_id": job_id,
            "url": url,
            "selectors": json.dumps(job_data.get("selectors") or {}),
            "engine": job_data.get("engine", "auto"),
            "schedule": schedule,
            "timeout": int(job_data.get("timeout", 30)),
            "search_type": job_data.get("search_type", ""),
            "tags": json.dumps(job_data.get("tags") or []),
            "wait_for": job_data.get("wait_for", "networkidle"),
            "screenshot": int(bool(job_data.get("screenshot", False))),
            "scroll": int(bool(job_data.get("scroll", True))),
            "status": STATUS_PENDING,
            "created_at": now,
            "updated_at": now,
            "next_run": next_run.isoformat() if next_run else None,
            "last_run": None,
            "run_count": 0,
            "celery_task_id": None,
            "error": None,
            "result_json": None,
            "duration_ms": None,
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, url, selectors, engine, schedule, timeout,
                    search_type, tags, wait_for, screenshot, scroll,
                    status, created_at, updated_at, next_run, last_run,
                    run_count, celery_task_id, error, result_json, duration_ms
                ) VALUES (
                    :job_id, :url, :selectors, :engine, :schedule, :timeout,
                    :search_type, :tags, :wait_for, :screenshot, :scroll,
                    :status, :created_at, :updated_at, :next_run, :last_run,
                    :run_count, :celery_task_id, :error, :result_json, :duration_ms
                )
                """,
                record,
            )
            conn.commit()

        logger.info("JobManager.create() | job_id=%s | url=%s | schedule=%s", job_id, url, schedule)
        return job_id

    def get(self, job_id: str) -> dict | None:
        """Retorna um job pelo ID ou None se não encontrado."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """
        Lista jobs com filtros opcionais.

        Parâmetros
        ----------
        status : str, optional
            Filtra por status (pending, running, completed, failed, etc.)
        limit : int
            Máximo de resultados (padrão 100).
        offset : int
            Offset para paginação.
        tags : list[str], optional
            Filtra jobs que contenham todos os tags.
        """
        query = "SELECT * FROM jobs"
        params: list = []
        conditions: list[str] = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        jobs = [self._row_to_dict(r) for r in rows]

        # Filtra por tags (post-query — SQLite não tem array ops nativos)
        if tags:
            jobs = [
                j for j in jobs
                if all(t in j.get("tags", []) for t in tags)
            ]

        return jobs

    def update_status(
        self,
        job_id: str,
        status: str,
        error: str | None = None,
        result: dict | None = None,
        duration_ms: float | None = None,
        celery_task_id: str | None = None,
    ) -> bool:
        """
        Atualiza o status de um job.

        Parâmetros
        ----------
        job_id : str
        status : str — um dos VALID_STATUSES
        error : str, optional — mensagem de erro
        result : dict, optional — resultado normalizado
        duration_ms : float, optional — duração da execução
        celery_task_id : str, optional — ID da task Celery

        Retorno
        -------
        bool : True se atualizado, False se job não encontrado.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Status inválido: {status}. Válidos: {VALID_STATUSES}")

        now = datetime.now(timezone.utc).isoformat()
        updates: dict = {"status": status, "updated_at": now}

        if error is not None:
            updates["error"] = error

        if result is not None:
            updates["result_json"] = json.dumps(result, ensure_ascii=False)

        if duration_ms is not None:
            updates["duration_ms"] = duration_ms

        if celery_task_id is not None:
            updates["celery_task_id"] = celery_task_id

        if status == STATUS_RUNNING:
            updates["last_run"] = now

        if status in (STATUS_COMPLETED, STATUS_FAILED):
            # Incrementa contador de execuções
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE jobs SET run_count = run_count + 1 WHERE job_id = ?",
                    (job_id,),
                )

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [job_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE jobs SET {set_clause} WHERE job_id = ?", values
            )
            conn.commit()
            updated = cursor.rowcount > 0

        logger.debug("JobManager.update_status() | job_id=%s | status=%s", job_id, status)
        return updated

    def set_next_run(self, job_id: str, next_run: datetime) -> None:
        """Atualiza o próximo horário de execução de um job recorrente."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE jobs SET next_run=?, status=?, updated_at=? WHERE job_id=?",
                (
                    next_run.isoformat(),
                    STATUS_PENDING,
                    datetime.now(timezone.utc).isoformat(),
                    job_id,
                ),
            )
            conn.commit()

    def cancel(self, job_id: str) -> bool:
        """Cancela um job pendente ou em fila."""
        job = self.get(job_id)
        if not job:
            return False
        if job["status"] in (STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED):
            return False
        return self.update_status(job_id, status=STATUS_CANCELLED)

    def delete(self, job_id: str) -> bool:
        """Remove um job permanentemente."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
            conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("JobManager.delete() | job_id=%s removido", job_id)
        return deleted

    # ------------------------------------------------------------------
    # Consultas especiais
    # ------------------------------------------------------------------

    def get_due_jobs(self, now: datetime | None = None) -> list[dict]:
        """
        Retorna jobs agendados que estão prontos para execução
        (next_run <= agora + 60s de tolerância).
        """
        now = now or datetime.now(timezone.utc)
        threshold = now.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = ?
                AND next_run IS NOT NULL
                AND next_run <= ?
                ORDER BY next_run ASC
                LIMIT 100
                """,
                (STATUS_PENDING, threshold),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Retorna estatísticas gerais dos jobs."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as count FROM jobs GROUP BY status"
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            avg_duration = conn.execute(
                "SELECT AVG(duration_ms) FROM jobs WHERE duration_ms IS NOT NULL"
            ).fetchone()[0]

        by_status = {row[0]: row[1] for row in rows}
        return {
            "total": total,
            "by_status": by_status,
            "avg_duration_ms": round(avg_duration, 2) if avg_duration else None,
        }

    def cleanup_old(self, days: int = 30) -> int:
        """Remove jobs concluídos/cancelados mais antigos que `days` dias."""
        threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM jobs
                WHERE status IN (?, ?, ?)
                AND updated_at < ?
                """,
                (STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED, threshold),
            )
            conn.commit()
        removed = cursor.rowcount
        logger.info("JobManager.cleanup_old() | removidos=%d | threshold=%s", removed, threshold)
        return removed

    # ------------------------------------------------------------------
    # SQLite setup
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id         TEXT PRIMARY KEY,
                    url            TEXT NOT NULL,
                    selectors      TEXT NOT NULL DEFAULT '{}',
                    engine         TEXT NOT NULL DEFAULT 'auto',
                    schedule       TEXT NOT NULL DEFAULT '',
                    timeout        INTEGER NOT NULL DEFAULT 30,
                    search_type    TEXT NOT NULL DEFAULT '',
                    tags           TEXT NOT NULL DEFAULT '[]',
                    wait_for       TEXT NOT NULL DEFAULT 'networkidle',
                    screenshot     INTEGER NOT NULL DEFAULT 0,
                    scroll         INTEGER NOT NULL DEFAULT 1,
                    status         TEXT NOT NULL DEFAULT 'pending',
                    created_at     TEXT NOT NULL,
                    updated_at     TEXT NOT NULL,
                    next_run       TEXT,
                    last_run       TEXT,
                    run_count      INTEGER NOT NULL DEFAULT 0,
                    celery_task_id TEXT,
                    error          TEXT,
                    result_json    TEXT,
                    duration_ms    REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs(next_run)"
            )
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        # Deserializa campos JSON
        for field in ("selectors", "tags"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    d[field] = {} if field == "selectors" else []
        if isinstance(d.get("result_json"), str):
            try:
                d["result"] = json.loads(d["result_json"])
            except (json.JSONDecodeError, TypeError):
                d["result"] = None
            del d["result_json"]
        # Booleanos
        d["screenshot"] = bool(d.get("screenshot", 0))
        d["scroll"] = bool(d.get("scroll", 1))
        return d
