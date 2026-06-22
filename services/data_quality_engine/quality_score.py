"""
QualityScorer — calcula score de qualidade 0-100 para datasets scraped.

Dimensões (pontuação máxima):
  Completude (campos preenchidos)        → 30 pts
  Consistência de tipos                  → 20 pts
  Unicidade (sem duplicatas)             → 20 pts
  Validade (valores não-nulos/vazios)    → 20 pts
  Formato (emails, URLs, datas válidos)  → 10 pts

Total: 0–100 com grade A/B/C/D/F.
"""

import logging
import re
import statistics
from typing import Any

logger = logging.getLogger(__name__)

# Patterns de validação de formato
_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_RE_URL = re.compile(r"^https?://[^\s\"'<>]{3,}$")
_RE_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?")
_RE_DATE_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_PHONE = re.compile(r"^[\+\d\s\-\(\)]{7,20}$")


class QualityScorer:
    """
    Calcula score de qualidade para datasets scraped.

    Exemplo de uso
    --------------
    scorer = QualityScorer()
    result = scorer.score(
        data=[{"nome": "Iris", "email": "iris@ex.com"}, {"nome": "Bob", "email": None}],
        schema={"nome": {"required": True}, "email": {"required": False, "type": "email"}},
    )
    # result["score"] → int 0-100
    # result["grade"] → "A"/"B"/"C"/"D"/"F"
    # result["issues"] → list[str]
    # result["recommendations"] → list[str]
    """

    def score(
        self,
        data: list[dict],
        schema: dict | None = None,
    ) -> dict[str, Any]:
        """
        Calcula o score de qualidade.

        Parâmetros
        ----------
        data : list[dict]
            Lista de itens scraped (cada item é um dict de campos).
        schema : dict, optional
            Schema esperado: {campo: {required: bool, type: str}}.
            Se None, infere os campos a partir dos dados.

        Retorno
        -------
        dict com:
            score : int (0-100)
            grade : str ("A", "B", "C", "D", "F")
            breakdown : dict (pontuação por dimensão)
            items_count : int
            fields_count : int
            issues : list[str]
            recommendations : list[str]
        """
        if not data:
            return {
                "score": 0,
                "grade": "F",
                "breakdown": {
                    "completeness": 0,
                    "type_consistency": 0,
                    "uniqueness": 0,
                    "validity": 0,
                    "format": 0,
                },
                "items_count": 0,
                "fields_count": 0,
                "issues": ["Dataset vazio — nenhum item para avaliar."],
                "recommendations": [
                    "Verificar se a URL está correta.",
                    "Verificar seletores CSS/XPath.",
                    "Considerar usar Playwright para páginas com JavaScript.",
                ],
            }

        issues: list[str] = []
        recommendations: list[str] = []

        all_keys = self._collect_keys(data, schema)

        # ── 1. Completude (30 pts) ─────────────────────────────────────────
        completeness, completeness_issues = self._score_completeness(data, all_keys, schema)
        issues.extend(completeness_issues)
        if completeness < 20:
            recommendations.append(
                "Muitos campos vazios. Revisar seletores CSS/XPath para garantir cobertura."
            )

        # ── 2. Consistência de tipos (20 pts) ─────────────────────────────
        type_consistency, type_issues = self._score_type_consistency(data, all_keys)
        issues.extend(type_issues)
        if type_issues:
            recommendations.append(
                "Campos com tipos inconsistentes detectados. Considerar result_normalizer."
            )

        # ── 3. Unicidade — sem duplicatas (20 pts) ────────────────────────
        uniqueness, dup_issues = self._score_uniqueness(data)
        issues.extend(dup_issues)
        if dup_issues:
            recommendations.append(
                "Duplicatas detectadas. Verificar paginação ou adicionar campo de ID único."
            )

        # ── 4. Validade — valores não-nulos/vazios (20 pts) ───────────────
        validity, validity_issues = self._score_validity(data)
        issues.extend(validity_issues)
        if validity < 10:
            recommendations.append(
                "Muitos itens com valores inválidos ou nulos. Verificar parsing dos dados."
            )

        # ── 5. Formato — emails, URLs, datas (10 pts) ────────────────────
        format_score, format_issues = self._score_format(data, schema)
        issues.extend(format_issues)
        if format_issues:
            recommendations.append(
                "Valores com formato inválido detectados. Verificar normalização."
            )

        total = int(completeness + type_consistency + uniqueness + validity + format_score)
        total = max(0, min(100, total))

        if not issues:
            recommendations.append(
                "Dados com boa qualidade — nenhuma ação corretiva necessária."
            )

        logger.info(
            "QualityScorer.score() | itens=%d | score=%d | grade=%s",
            len(data), total, self._grade(total),
        )

        return {
            "score": total,
            "grade": self._grade(total),
            "breakdown": {
                "completeness": round(completeness, 2),
                "type_consistency": round(type_consistency, 2),
                "uniqueness": round(uniqueness, 2),
                "validity": round(validity, 2),
                "format": round(format_score, 2),
            },
            "items_count": len(data),
            "fields_count": len(all_keys),
            "issues": issues,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Dimensões de score
    # ------------------------------------------------------------------

    def _score_completeness(
        self,
        data: list[dict],
        all_keys: set[str],
        schema: dict | None,
    ) -> tuple[float, list[str]]:
        """Completude: quantos campos esperados estão preenchidos."""
        if not all_keys:
            return 30.0, []

        issues: list[str] = []
        total_cells = len(data) * len(all_keys)
        filled_cells = sum(
            1 for item in data
            for key in all_keys
            if item.get(key) not in (None, "", [], {})
        )
        rate = filled_cells / total_cells if total_cells else 1.0
        score = rate * 30

        missing_pct = round((1 - rate) * 100, 1)
        if missing_pct > 30:
            issues.append(f"Completude: {missing_pct}% dos campos estão vazios/ausentes.")

        # Campos obrigatórios por schema
        if schema:
            for field, rules in schema.items():
                if rules.get("required"):
                    missing = sum(
                        1 for item in data
                        if item.get(field) in (None, "", [], {})
                    )
                    if missing > 0:
                        issues.append(
                            f"Campo obrigatório '{field}' ausente em {missing}/{len(data)} itens."
                        )

        return score, issues

    def _score_type_consistency(
        self, data: list[dict], all_keys: set[str]
    ) -> tuple[float, list[str]]:
        """Consistência: cada campo deve ter tipo consistente entre itens."""
        score = 20.0
        issues: list[str] = []

        type_map: dict[str, set] = {}
        for item in data:
            for key in all_keys:
                val = item.get(key)
                if val is not None and val != "":
                    type_map.setdefault(key, set()).add(type(val).__name__)

        for field, types in type_map.items():
            n_types = len(types)
            if n_types == 2 and {"list", "str"} >= types:
                # str e list são comuns juntos — penalidade leve
                score -= 1
            elif n_types >= 3:
                score -= 4
                issues.append(
                    f"Campo '{field}' tem tipos inconsistentes: {types}."
                )
            elif n_types == 2 and types not in [{"int", "float"}]:
                score -= 2
                issues.append(
                    f"Campo '{field}' mistura tipos: {types}."
                )

        return max(0.0, score), issues

    def _score_uniqueness(self, data: list[dict]) -> tuple[float, list[str]]:
        """Unicidade: penaliza duplicatas exatas."""
        from .duplicate_detector import DuplicateDetector
        dup_result = DuplicateDetector().detect(data)
        dup_rate = dup_result["duplicate_rate"]
        score = max(0.0, 20.0 * (1 - dup_rate))

        issues: list[str] = []
        if dup_rate > 0.05:
            issues.append(
                f"Unicidade: {dup_result['duplicates_count']} duplicatas detectadas "
                f"({round(dup_rate * 100, 1)}% do total)."
            )
        return score, issues

    def _score_validity(self, data: list[dict]) -> tuple[float, list[str]]:
        """Validade: itens com pelo menos um campo não-vazio e sem valores placeholder."""
        score = 20.0
        issues: list[str] = []

        _PLACEHOLDER = {"n/a", "na", "null", "none", "undefined", "-", "--", "n.a.", "n.d."}
        total = len(data)
        empty_items = 0
        placeholder_count = 0

        for item in data:
            values = [v for v in item.values() if v not in (None, "", [], {})]
            if not values:
                empty_items += 1
                continue
            # Detecta placeholders
            for v in values:
                if isinstance(v, str) and v.strip().lower() in _PLACEHOLDER:
                    placeholder_count += 1

        if empty_items > 0:
            penalty = min(20.0, (empty_items / total) * 20)
            score -= penalty
            issues.append(f"Validade: {empty_items} itens completamente vazios.")

        if placeholder_count > 0:
            penalty = min(10.0, (placeholder_count / (total * 3)) * 10)
            score -= penalty
            if placeholder_count > 5:
                issues.append(
                    f"Validade: {placeholder_count} valores placeholder detectados (N/A, null, -)."
                )

        return max(0.0, score), issues

    def _score_format(
        self,
        data: list[dict],
        schema: dict | None,
    ) -> tuple[float, list[str]]:
        """Formato: valida emails, URLs, datas e telefones."""
        score = 10.0
        issues: list[str] = []
        format_errors = 0

        validators = {
            "email": _RE_EMAIL,
            "url": _RE_URL,
            "href": _RE_URL,
            "link": _RE_URL,
            "date": _RE_DATE_ISO,
            "data": _RE_DATE_ISO,
            "phone": _RE_PHONE,
            "telefone": _RE_PHONE,
        }

        # Adiciona validadores do schema
        schema_validators: dict[str, re.Pattern] = {}
        if schema:
            for field, rules in schema.items():
                t = rules.get("type", "")
                if t in ("email",):
                    schema_validators[field] = _RE_EMAIL
                elif t in ("url",):
                    schema_validators[field] = _RE_URL
                elif t in ("date_iso",):
                    schema_validators[field] = _RE_DATE_ISO

        for item in data:
            for key, value in item.items():
                if not isinstance(value, str) or not value.strip():
                    continue
                # Verifica pelo nome do campo
                key_lower = key.lower()
                for hint, pattern in validators.items():
                    if hint in key_lower and not pattern.match(value.strip()):
                        format_errors += 1
                        break
                # Verifica pelo schema
                if key in schema_validators:
                    if not schema_validators[key].match(value.strip()):
                        format_errors += 1

        if format_errors > 0:
            total_values = sum(
                1 for item in data
                for v in item.values()
                if isinstance(v, str) and v.strip()
            ) or 1
            error_rate = format_errors / total_values
            penalty = min(10.0, error_rate * 20)
            score -= penalty
            issues.append(
                f"Formato: {format_errors} valores com formato inválido (email/URL/data/telefone)."
            )

        return max(0.0, score), issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_keys(data: list[dict], schema: dict | None) -> set[str]:
        """Coleta todos os campos presentes nos dados ou no schema."""
        keys: set[str] = set()
        for item in data:
            keys.update(item.keys())
        if schema:
            keys.update(schema.keys())
        return keys

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"
