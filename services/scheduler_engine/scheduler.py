"""
Scheduler — lógica de agendamento baseada em expressões cron e intervalos.

Suporta:
- Expressões cron padrão (5 campos: min hora dia mês diasemana)
- Intervalos simples: "every_5m", "every_1h", "every_1d", "every_1w"
- Datas específicas ISO8601

Usa croniter para parsing de expressões cron.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Mapeamento de intervalos simples
_INTERVAL_MAP = {
    "every_1m": timedelta(minutes=1),
    "every_5m": timedelta(minutes=5),
    "every_10m": timedelta(minutes=10),
    "every_15m": timedelta(minutes=15),
    "every_30m": timedelta(minutes=30),
    "every_1h": timedelta(hours=1),
    "every_2h": timedelta(hours=2),
    "every_6h": timedelta(hours=6),
    "every_12h": timedelta(hours=12),
    "every_1d": timedelta(days=1),
    "every_1w": timedelta(weeks=1),
}


def compute_next_run(schedule: str, from_dt: datetime | None = None) -> datetime | None:
    """
    Calcula a próxima data/hora de execução dado um schedule.

    Parâmetros
    ----------
    schedule : str
        - Intervalo: "every_5m", "every_1h", "every_1d", etc.
        - Cron: "*/5 * * * *", "0 8 * * 1-5", etc.
        - ISO8601 único: "2025-01-15T10:00:00Z"
        - Vazio / None: None (sem agendamento)

    from_dt : datetime, optional
        Data de referência (padrão: agora em UTC).

    Retorno
    -------
    datetime em UTC ou None se sem agendamento.
    """
    if not schedule:
        return None

    now = from_dt or datetime.now(timezone.utc)

    # Intervalo simples
    if schedule in _INTERVAL_MAP:
        return now + _INTERVAL_MAP[schedule]

    # ISO8601 único
    if re.match(r"\d{4}-\d{2}-\d{2}", schedule):
        try:
            dt = datetime.fromisoformat(schedule.replace("Z", "+00:00"))
            return dt if dt > now else None
        except ValueError:
            pass

    # Expressão cron
    return _next_from_cron(schedule, now)


def _next_from_cron(cron_expr: str, now: datetime) -> datetime | None:
    """Calcula próxima execução de uma expressão cron usando croniter."""
    try:
        from croniter import croniter  # type: ignore[import]
        it = croniter(cron_expr, now)
        return it.get_next(datetime).replace(tzinfo=timezone.utc)
    except ImportError:
        logger.warning(
            "croniter não instalado. Instale com: pip install croniter. "
            "Usando fallback de 1 hora."
        )
        return now + timedelta(hours=1)
    except Exception as exc:
        logger.error("Erro ao parsear cron '%s': %s", cron_expr, exc)
        return None


def is_due(next_run: datetime | None, tolerance_seconds: int = 60) -> bool:
    """
    Verifica se o job está na hora de ser executado.

    Parâmetros
    ----------
    next_run : datetime | None
        Próxima data agendada (UTC).
    tolerance_seconds : int
        Janela de tolerância em segundos (padrão 60).
    """
    if next_run is None:
        return False
    now = datetime.now(timezone.utc)
    delta = (next_run - now).total_seconds()
    return delta <= tolerance_seconds


def describe_schedule(schedule: str) -> str:
    """
    Retorna descrição human-readable do schedule.

    Exemplos:
        "every_1h" → "A cada 1 hora"
        "0 8 * * *" → "Cron: 0 8 * * *"
        "2025-01-15T10:00:00Z" → "Uma vez em 2025-01-15T10:00:00"
    """
    if not schedule:
        return "Sem agendamento"

    if schedule in _INTERVAL_MAP:
        labels = {
            "every_1m": "A cada 1 minuto",
            "every_5m": "A cada 5 minutos",
            "every_10m": "A cada 10 minutos",
            "every_15m": "A cada 15 minutos",
            "every_30m": "A cada 30 minutos",
            "every_1h": "A cada 1 hora",
            "every_2h": "A cada 2 horas",
            "every_6h": "A cada 6 horas",
            "every_12h": "A cada 12 horas",
            "every_1d": "Diariamente",
            "every_1w": "Semanalmente",
        }
        return labels.get(schedule, f"Intervalo: {schedule}")

    if re.match(r"\d{4}-\d{2}-\d{2}", schedule):
        return f"Uma vez em {schedule}"

    return f"Cron: {schedule}"


def validate_schedule(schedule: str) -> tuple[bool, str]:
    """
    Valida se um schedule é válido.

    Retorno
    -------
    (True, "") se válido; (False, mensagem_erro) se inválido.
    """
    if not schedule:
        return True, ""  # Sem agendamento é válido

    if schedule in _INTERVAL_MAP:
        return True, ""

    if re.match(r"\d{4}-\d{2}-\d{2}", schedule):
        try:
            datetime.fromisoformat(schedule.replace("Z", "+00:00"))
            return True, ""
        except ValueError:
            return False, f"Data ISO8601 inválida: {schedule}"

    # Valida cron
    try:
        from croniter import croniter
        if croniter.is_valid(schedule):
            return True, ""
        return False, f"Expressão cron inválida: {schedule}"
    except ImportError:
        # Sem croniter, valida formato básico (5 campos)
        parts = schedule.split()
        if len(parts) == 5:
            return True, ""
        return False, f"Expressão cron deve ter 5 campos: {schedule}"
    except Exception as exc:
        return False, str(exc)
