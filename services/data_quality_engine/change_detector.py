"""
ChangeDetector — detecta mudanças significativas entre runs do mesmo job.

Analisa:
- Mudança de volume (contagem de itens)
- Campos que sumiram ou apareceram
- Mudança em valores numéricos (preços, scores, etc.)
- Mudança no score de qualidade geral
- Novos padrões de dados (campos com valores novos)

Severidades: ok | info | warning | critical
"""

import logging
import statistics
from typing import Any

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    Compara dois snapshots do mesmo scraping e detecta mudanças significativas.

    Exemplo de uso
    --------------
    detector = ChangeDetector()

    result = detector.compare(old_data, new_data)
    print(result["severity"])   # "warning"
    print(result["changes"])    # lista de mudanças detectadas
    print(result["summary"])    # resumo textual
    """

    # Thresholds configuráveis
    THRESHOLDS: dict[str, Any] = {
        "count_change_pct": 20.0,       # Alerta se volume mudar > 20%
        "count_change_critical_pct": 50.0,  # Crítico se mudar > 50%
        "value_change_pct": 30.0,       # Alerta em variação de média numérica > 30%
        "value_change_critical_pct": 70.0,  # Crítico se > 70%
        "field_disappear": True,        # Alerta se campo desaparecer
        "new_fields": True,             # Info se campos novos aparecerem
        "quality_score_drop": 15,       # Alerta se score de qualidade cair > 15 pontos
    }

    def __init__(self, thresholds: dict | None = None) -> None:
        if thresholds:
            self.THRESHOLDS = {**self.THRESHOLDS, **thresholds}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def compare(
        self,
        old_data: list[dict],
        new_data: list[dict],
        old_quality_score: float | None = None,
        new_quality_score: float | None = None,
    ) -> dict[str, Any]:
        """
        Compara dois snapshots de dados do mesmo scraping.

        Parâmetros
        ----------
        old_data : list[dict]
            Dados da execução anterior.
        new_data : list[dict]
            Dados da execução atual.
        old_quality_score : float, optional
            Score QA da execução anterior (0-100).
        new_quality_score : float, optional
            Score QA da execução atual (0-100).

        Retorno
        -------
        dict com:
            changes : list[dict] — mudanças detectadas com tipo e severidade
            severity : str — "ok" | "info" | "warning" | "critical"
            summary : str — resumo textual
            old_count : int
            new_count : int
            count_change_pct : float
            recommendations : list[str]
        """
        if not old_data:
            return {
                "changes": [],
                "severity": "info",
                "summary": "Primeira execução — sem dados anteriores para comparação.",
                "old_count": 0,
                "new_count": len(new_data),
                "count_change_pct": 0.0,
                "recommendations": [],
            }

        if not new_data:
            return {
                "changes": [{"type": "no_data", "severity": "critical",
                              "message": "Execução atual retornou zero itens."}],
                "severity": "critical",
                "summary": "CRÍTICO: nenhum dado retornado nesta execução.",
                "old_count": len(old_data),
                "new_count": 0,
                "count_change_pct": -100.0,
                "recommendations": [
                    "Verificar se a URL ainda está acessível.",
                    "Verificar se o site mudou a estrutura HTML.",
                    "Verificar se há bloqueio de bot/CAPTCHA.",
                ],
            }

        changes: list[dict] = []
        recommendations: list[str] = []

        old_fields = self._collect_fields(old_data)
        new_fields = self._collect_fields(new_data)

        # 1. Mudança de volume
        volume_change = self._check_volume(old_data, new_data)
        if volume_change:
            changes.append(volume_change)
            if volume_change["severity"] in ("warning", "critical"):
                recommendations.append(
                    "Volume de itens mudou significativamente. "
                    "Verificar paginação, filtros e estrutura do site."
                )

        # 2. Campos que desapareceram
        disappeared = old_fields - new_fields
        if disappeared:
            severity = "critical" if self.THRESHOLDS["field_disappear"] else "info"
            changes.append({
                "type": "fields_disappeared",
                "severity": severity,
                "message": f"Campos removidos da estrutura: {', '.join(sorted(disappeared))}",
                "fields": sorted(disappeared),
            })
            recommendations.append(
                f"Campos desapareceram: {', '.join(sorted(disappeared))}. "
                "O site pode ter mudado a estrutura HTML. Revisar seletores."
            )

        # 3. Campos novos
        appeared = new_fields - old_fields
        if appeared and self.THRESHOLDS["new_fields"]:
            changes.append({
                "type": "fields_appeared",
                "severity": "info",
                "message": f"Novos campos detectados: {', '.join(sorted(appeared))}",
                "fields": sorted(appeared),
            })

        # 4. Mudança em valores numéricos
        common_fields = old_fields & new_fields
        numeric_changes = self._check_numeric_changes(old_data, new_data, common_fields)
        changes.extend(numeric_changes)
        if any(c["severity"] == "critical" for c in numeric_changes):
            recommendations.append(
                "Valores numéricos mudaram drasticamente. Verificar se os dados ainda são válidos."
            )

        # 5. Mudança no score de qualidade
        if old_quality_score is not None and new_quality_score is not None:
            score_change = self._check_quality_score(old_quality_score, new_quality_score)
            if score_change:
                changes.append(score_change)
                if score_change["severity"] in ("warning", "critical"):
                    recommendations.append(
                        "Qualidade dos dados degradou. Verificar seletores e estrutura do site."
                    )

        # 6. Mudança em campos de texto (diversidade de valores)
        text_changes = self._check_text_diversity(old_data, new_data, common_fields)
        changes.extend(text_changes)

        # Determina severidade geral
        severity = self._aggregate_severity(changes)

        count_pct = round(((len(new_data) - len(old_data)) / len(old_data)) * 100, 2)

        summary = self._build_summary(changes, len(old_data), len(new_data))

        logger.info(
            "ChangeDetector.compare() | changes=%d | severity=%s | vol: %d→%d",
            len(changes), severity, len(old_data), len(new_data),
        )

        return {
            "changes": changes,
            "severity": severity,
            "summary": summary,
            "old_count": len(old_data),
            "new_count": len(new_data),
            "count_change_pct": count_pct,
            "recommendations": recommendations,
        }

    def has_significant_changes(
        self, old_data: list[dict], new_data: list[dict]
    ) -> bool:
        """
        Retorna True se houver mudanças de nível warning ou critical.
        Atalho para compare() quando só precisa saber se houve mudança relevante.
        """
        result = self.compare(old_data, new_data)
        return result["severity"] in ("warning", "critical")

    # ------------------------------------------------------------------
    # Análises individuais
    # ------------------------------------------------------------------

    def _check_volume(self, old: list, new: list) -> dict | None:
        """Verifica mudança de volume (contagem de itens)."""
        old_n = len(old)
        new_n = len(new)
        if old_n == 0:
            return None

        pct = ((new_n - old_n) / old_n) * 100
        abs_pct = abs(pct)
        direction = "aumentou" if pct > 0 else "diminuiu"

        if abs_pct > self.THRESHOLDS["count_change_critical_pct"]:
            return {
                "type": "count_change",
                "severity": "critical",
                "message": f"Volume de itens {direction} {abs_pct:.1f}%: {old_n} → {new_n}",
                "old": old_n,
                "new": new_n,
                "change_pct": round(pct, 2),
            }
        elif abs_pct > self.THRESHOLDS["count_change_pct"]:
            return {
                "type": "count_change",
                "severity": "warning",
                "message": f"Volume de itens {direction} {abs_pct:.1f}%: {old_n} → {new_n}",
                "old": old_n,
                "new": new_n,
                "change_pct": round(pct, 2),
            }
        return None

    def _check_numeric_changes(
        self,
        old: list[dict],
        new: list[dict],
        fields: set[str],
    ) -> list[dict]:
        """Detecta mudanças significativas em campos numéricos."""
        changes: list[dict] = []

        for field in sorted(fields):
            old_nums = self._extract_numbers(old, field)
            new_nums = self._extract_numbers(new, field)

            if len(old_nums) < 3 or len(new_nums) < 3:
                continue

            old_mean = statistics.mean(old_nums)
            new_mean = statistics.mean(new_nums)

            if old_mean == 0:
                continue

            pct = abs((new_mean - old_mean) / old_mean) * 100

            if pct > self.THRESHOLDS["value_change_critical_pct"]:
                changes.append({
                    "type": "value_change",
                    "severity": "critical",
                    "field": field,
                    "message": (
                        f"Média de '{field}' mudou {pct:.1f}%: "
                        f"{old_mean:.2f} → {new_mean:.2f}"
                    ),
                    "old_mean": round(old_mean, 4),
                    "new_mean": round(new_mean, 4),
                    "change_pct": round(pct, 2),
                })
            elif pct > self.THRESHOLDS["value_change_pct"]:
                changes.append({
                    "type": "value_change",
                    "severity": "warning",
                    "field": field,
                    "message": (
                        f"Média de '{field}' mudou {pct:.1f}%: "
                        f"{old_mean:.2f} → {new_mean:.2f}"
                    ),
                    "old_mean": round(old_mean, 4),
                    "new_mean": round(new_mean, 4),
                    "change_pct": round(pct, 2),
                })

        return changes

    def _check_quality_score(
        self, old_score: float, new_score: float
    ) -> dict | None:
        """Detecta queda no score de qualidade."""
        drop = old_score - new_score
        if drop <= 0:
            return None

        if drop >= self.THRESHOLDS["quality_score_drop"] * 2:
            severity = "critical"
        elif drop >= self.THRESHOLDS["quality_score_drop"]:
            severity = "warning"
        else:
            return None

        return {
            "type": "quality_degradation",
            "severity": severity,
            "message": f"Score de qualidade caiu {drop:.1f} pontos: {old_score:.0f} → {new_score:.0f}",
            "old_score": old_score,
            "new_score": new_score,
            "drop": round(drop, 2),
        }

    def _check_text_diversity(
        self,
        old: list[dict],
        new: list[dict],
        fields: set[str],
    ) -> list[dict]:
        """Detecta se a diversidade de valores textuais mudou drasticamente."""
        changes: list[dict] = []

        for field in sorted(fields):
            old_uniq = len({str(item.get(field, "")) for item in old if item.get(field)})
            new_uniq = len({str(item.get(field, "")) for item in new if item.get(field)})

            if old_uniq < 5 or new_uniq == 0:
                continue

            # Se quantidade de valores únicos caiu muito (possível conteúdo repetido)
            diversity_pct = (new_uniq / old_uniq) if old_uniq else 1.0
            if diversity_pct < 0.2:
                changes.append({
                    "type": "diversity_drop",
                    "severity": "warning",
                    "field": field,
                    "message": (
                        f"Campo '{field}' perdeu diversidade: "
                        f"{old_uniq} valores únicos → {new_uniq} (possível conteúdo estático/erro)"
                    ),
                    "old_unique": old_uniq,
                    "new_unique": new_uniq,
                })

        return changes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_fields(data: list[dict]) -> set[str]:
        """Coleta todos os campos presentes nos dados."""
        fields: set[str] = set()
        for item in data:
            fields.update(item.keys())
        return fields

    @staticmethod
    def _extract_numbers(data: list[dict], field: str) -> list[float]:
        """Extrai valores numéricos de um campo, tentando converter strings."""
        numbers: list[float] = []
        for item in data:
            val = item.get(field)
            if val is None:
                continue
            try:
                numbers.append(float(str(val).replace(",", ".").replace("R$", "").replace(" ", "")))
            except (ValueError, TypeError):
                pass
        return numbers

    @staticmethod
    def _aggregate_severity(changes: list[dict]) -> str:
        """Determina severidade geral com base nas mudanças."""
        if not changes:
            return "ok"
        severities = {c.get("severity", "info") for c in changes}
        if "critical" in severities:
            return "critical"
        if "warning" in severities:
            return "warning"
        return "info"

    @staticmethod
    def _build_summary(changes: list[dict], old_n: int, new_n: int) -> str:
        """Constrói resumo textual."""
        if not changes:
            return f"Nenhuma mudança significativa detectada ({old_n} → {new_n} itens)."

        n = len(changes)
        critical = sum(1 for c in changes if c.get("severity") == "critical")
        warnings = sum(1 for c in changes if c.get("severity") == "warning")

        parts = [f"{n} mudança(s) detectada(s)"]
        if critical:
            parts.append(f"{critical} crítica(s)")
        if warnings:
            parts.append(f"{warnings} aviso(s)")
        parts.append(f"{old_n} → {new_n} itens")

        return " | ".join(parts) + "."
