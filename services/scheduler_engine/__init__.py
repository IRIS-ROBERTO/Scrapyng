"""
Scheduler Engine — agendamento e execução assíncrona de jobs de scraping.

Usa Celery + Redis como broker/backend. Exporta a app Celery e as tasks.
"""

from .celery_app import app
from .tasks import execute_scraping_job, check_and_trigger_scheduled_jobs
from .job_manager import JobManager

__all__ = [
    "app",
    "execute_scraping_job",
    "check_and_trigger_scheduled_jobs",
    "JobManager",
]
