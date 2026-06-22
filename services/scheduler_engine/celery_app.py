"""
Configuração da aplicação Celery para o WebScrapy AI Platform.

Broker e backend: Redis (configurável via env vars).
Timezone: America/Sao_Paulo.
"""

import os

from celery import Celery
from celery.schedules import crontab

# ---------------------------------------------------------------------------
# Instância da app
# ---------------------------------------------------------------------------

app = Celery(
    "webscrapy",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
    include=["services.scheduler_engine.tasks"],
)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,
    # Confiabilidade
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Resultados
    result_expires=60 * 60 * 24 * 7,  # 7 dias
    task_result_extended=True,
    # Retry padrão de tasks
    task_max_retries=3,
    # Limites de tempo
    task_soft_time_limit=60 * 10,   # 10 minutos soft limit
    task_time_limit=60 * 15,         # 15 minutos hard limit
    # Logging
    worker_redirect_stdouts_level="INFO",
    # Compressão do resultado
    result_compression="gzip",
    # Rotas de filas
    task_routes={
        "services.scheduler_engine.tasks.execute_scraping_job": {"queue": "scraping"},
        "services.scheduler_engine.tasks.check_and_trigger_scheduled_jobs": {"queue": "scheduler"},
    },
    # Definição das filas
    task_queues={
        "scraping": {"exchange": "scraping", "routing_key": "scraping"},
        "scheduler": {"exchange": "scheduler", "routing_key": "scheduler"},
        "default": {"exchange": "default", "routing_key": "default"},
    },
    task_default_queue="default",
)

# ---------------------------------------------------------------------------
# Beat schedule — tarefas periódicas
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    # Verifica jobs agendados a cada minuto
    "check-scheduled-jobs-every-minute": {
        "task": "services.scheduler_engine.tasks.check_and_trigger_scheduled_jobs",
        "schedule": crontab(minute="*"),  # a cada minuto
        "options": {"queue": "scheduler"},
    },
    # Limpeza de resultados antigos (diário às 3h)
    "cleanup-old-results-daily": {
        "task": "services.scheduler_engine.tasks.cleanup_old_results",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "scheduler"},
    },
}
