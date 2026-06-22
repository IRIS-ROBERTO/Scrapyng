"""
Data validation agent.

Validates the quality of structured data extracted by scrapers.
Checks completeness, format correctness, consistency, and outliers.
"""

from __future__ import annotations

import json
import re
import structlog
from typing import Any
from urllib.parse import urlparse

from .nvidia_client import NvidiaClient

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt for validation
# ---------------------------------------------------------------------------
_VALIDATION_SYSTEM_PROMPT = """Você é um especialista em qualidade de dados extraídos por web scrapers.
Sua função é validar a integridade e qualidade dos dados estruturados.

Verificações que você realiza:
1. COMPLETUDE: Campos obrigatórios preenchidos? Taxa de campos nulos?
2. FORMATO: Emails válidos? URLs absolutas? Datas em formato ISO? Preços numéricos?
3. CONSISTÊNCIA: Valores inconsistentes com o contexto? Moedas misturadas? Idiomas misturados?
4. OUTLIERS: Preços absurdos? Datas no futuro quando não esperado? Textos muito curtos ou longos?
5. DUPLICATAS: Registros suspeitos de duplicação parcial?

Para cada problema encontrado, você especifica:
- Campo afetado
- Índice do registro (se aplicável)
- Tipo do problema
- Sugestão de correção

Você SEMPRE retorna JSON válido sem markdown.

Formato de saída:
{
  "is_valid": true/false,
  "quality_score": "number (0-100)",
  "total_records": "number",
  "valid_records": "number",
  "issues": [
    {
      "type": "missing_field|invalid_format|inconsistency|outlier|duplicate|other",
      "severity": "critical|warning|info",
      "field": "string",
      "record_index": "number|null",
      "description": "string",
      "suggestion": "string|null"
    }
  ],
  "field_stats": {
    "campo_name": {
      "null_count": "number",
      "null_pct": "number",
      "unique_count": "number",
      "sample_values": ["até 3 exemplos"]
    }
  },
  "summary": "string (resumo executivo da qualidade dos dados)"
}"""


class DataValidationAgent:
    """
    Validates quality of structured scraped data.

    Runs two validation layers:
    1. **Rule-based** (fast, local): checks types, URL format, email regex, etc.
    2. **AI-based** (smart): contextual validation, outlier detection, consistency.

    Example
    -------
    ::

        agent = DataValidationAgent(nvidia_client)
        report = await agent.validate(
            data=[{"title": "iPhone 15", "price": 5999.0, "url": "https://..."}, ...],
            context="Produtos de smartphone",
            required_fields=["title", "price"],
        )
        print(report["quality_score"])
        for issue in report["issues"]:
            print(issue["severity"], issue["description"])
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def validate(
        self,
        data: list[dict],
        context: str,
        required_fields: list[str] | None = None,
        schema: dict | None = None,
    ) -> dict:
        """
        Run full validation pipeline on structured data.

        Parameters
        ----------
        data:
            List of structured data records.
        context:
            Description of what the data represents.
        required_fields:
            Fields that must be non-null in every record.
        schema:
            Optional schema dict (from DataStructuringAgent) for type checking.

        Returns
        -------
        dict
            Validation report with is_valid, quality_score, issues, field_stats, summary.
        """
        log.info("validation_agent_start", records=len(data), context=context)

        if not data:
            return self._empty_report()

        required_fields = required_fields or []

        # Layer 1: fast rule-based checks
        rule_issues = self._rule_based_validation(data, required_fields, schema)

        # Layer 2: AI contextual validation (send sample of up to 30 records)
        ai_report = await self._ai_validation(
            data=data[:30],
            context=context,
            required_fields=required_fields,
            rule_issues=rule_issues,
        )

        # Merge rule issues into AI report
        all_issues = rule_issues + [
            i for i in ai_report.get("issues", [])
            if i not in rule_issues
        ]

        # Recompute quality score combining both layers
        critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")

        ai_score = float(ai_report.get("quality_score", 50))
        penalty = min(50, critical_count * 15 + warning_count * 5)
        final_score = max(0, round(ai_score - penalty + (50 - ai_score) * 0.3))

        result = {
            **ai_report,
            "issues": all_issues,
            "quality_score": min(100, final_score),
            "is_valid": critical_count == 0,
            "total_records": len(data),
        }

        log.info(
            "validation_agent_done",
            score=result["quality_score"],
            issues=len(all_issues),
            critical=critical_count,
        )
        return result

    async def validate_field(
        self,
        field_name: str,
        values: list[Any],
        expected_type: str = "auto",
    ) -> dict:
        """
        Validate a single field across all records.

        Returns
        -------
        dict
            ``{"valid_count": int, "invalid_count": int, "issues": [...], "clean_values": [...]}``
        """
        null_count = sum(1 for v in values if v is None or v == "")
        non_null = [v for v in values if v is not None and v != ""]

        issues: list[dict] = []

        if expected_type == "email":
            pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            invalid = [v for v in non_null if not pattern.match(str(v))]
            if invalid:
                issues.append({
                    "type": "invalid_format",
                    "severity": "warning",
                    "field": field_name,
                    "description": f"{len(invalid)} valores de email inválidos.",
                    "examples": invalid[:3],
                })

        elif expected_type == "url":
            invalid = []
            for v in non_null:
                try:
                    parsed = urlparse(str(v))
                    if not parsed.scheme or not parsed.netloc:
                        invalid.append(v)
                except Exception:
                    invalid.append(v)
            if invalid:
                issues.append({
                    "type": "invalid_format",
                    "severity": "warning",
                    "field": field_name,
                    "description": f"{len(invalid)} URLs inválidas ou relativas.",
                    "examples": invalid[:3],
                })

        elif expected_type in ("price", "number"):
            invalid = [v for v in non_null if not isinstance(v, (int, float))]
            if invalid:
                issues.append({
                    "type": "invalid_format",
                    "severity": "critical",
                    "field": field_name,
                    "description": f"{len(invalid)} valores numéricos inválidos.",
                    "examples": invalid[:3],
                })

        valid_count = len(values) - len(issues) * 0  # simplified
        return {
            "field_name": field_name,
            "total_values": len(values),
            "null_count": null_count,
            "null_pct": round(null_count / len(values) * 100, 1) if values else 0,
            "issues": issues,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rule_based_validation(
        self,
        data: list[dict],
        required_fields: list[str],
        schema: dict | None,
    ) -> list[dict]:
        """Fast local validation rules — no API call needed."""
        issues: list[dict] = []

        for idx, record in enumerate(data):
            # Required field check
            for field in required_fields:
                val = record.get(field)
                if val is None or val == "" or val == []:
                    issues.append({
                        "type": "missing_field",
                        "severity": "critical",
                        "field": field,
                        "record_index": idx,
                        "description": f"Campo obrigatório '{field}' está vazio no registro {idx}.",
                        "suggestion": f"Revisar o seletor para '{field}'.",
                    })

            # URL validation
            for key, val in record.items():
                if key.endswith("_url") or key == "url":
                    if val and isinstance(val, str):
                        try:
                            parsed = urlparse(val)
                            if not parsed.scheme:
                                issues.append({
                                    "type": "invalid_format",
                                    "severity": "warning",
                                    "field": key,
                                    "record_index": idx,
                                    "description": f"URL relativa detectada em '{key}': {val[:80]}",
                                    "suggestion": "Aplicar urljoin com a URL base.",
                                })
                        except Exception:
                            pass

                # Price / numeric outlier check
                if key in ("price", "preco", "valor", "salary_min", "salary_max"):
                    if val is not None and isinstance(val, (int, float)):
                        if val < 0:
                            issues.append({
                                "type": "outlier",
                                "severity": "warning",
                                "field": key,
                                "record_index": idx,
                                "description": f"Valor negativo em '{key}': {val}",
                                "suggestion": "Verificar lógica de extração do campo.",
                            })

        return issues

    async def _ai_validation(
        self,
        data: list[dict],
        context: str,
        required_fields: list[str],
        rule_issues: list[dict],
    ) -> dict:
        """Send sample data to AI for contextual validation."""
        data_json = json.dumps(data, ensure_ascii=False, indent=2)
        required_str = ", ".join(required_fields) if required_fields else "nenhum especificado"
        rule_summary = (
            f"\nProblemas já detectados por regras locais: {len(rule_issues)}\n"
            if rule_issues
            else ""
        )

        prompt = (
            f"Valide a qualidade destes dados extraídos por web scraping.\n\n"
            f"Contexto: {context}\n"
            f"Campos obrigatórios: {required_str}\n"
            f"{rule_summary}\n"
            f"DADOS (amostra de até 30 registros):\n{data_json}\n\n"
            f"Analise completude, formato, consistência e outliers.\n"
            f"Retorne APENAS JSON válido com o relatório de validação."
        )

        return await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_VALIDATION_SYSTEM_PROMPT,
            max_tokens=3000,
        )

    @staticmethod
    def _empty_report() -> dict:
        return {
            "is_valid": False,
            "quality_score": 0,
            "total_records": 0,
            "valid_records": 0,
            "issues": [{"type": "missing_field", "severity": "critical",
                        "field": "dataset", "record_index": None,
                        "description": "Nenhum dado fornecido para validação.",
                        "suggestion": "Verificar se o scraper está extraindo dados."}],
            "field_stats": {},
            "summary": "Dataset vazio — nenhum dado para validar.",
        }
