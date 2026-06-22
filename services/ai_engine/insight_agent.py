"""
Insight agent.

Generates executive summaries, trend analysis, and actionable insights
from structured scraped datasets using NVIDIA NIM.
"""

from __future__ import annotations

import json
import statistics
import structlog
from typing import Any

from .nvidia_client import NvidiaClient

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_INSIGHT_SYSTEM_PROMPT = """Você é um analista de dados sênior especializado em interpretar dados
extraídos de pesquisas web. Sua função é transformar dados brutos em insights acionáveis.

Você produz:
1. RESUMO EXECUTIVO: O que os dados revelam em 2-3 parágrafos
2. PRINCIPAIS DESCOBERTAS: Top 5-7 insights mais relevantes
3. TENDÊNCIAS: Padrões detectados nos dados
4. ANOMALIAS: Outliers e dados suspeitos que merecem atenção
5. RECOMENDAÇÕES: Ações concretas baseadas nos dados
6. MÉTRICAS CHAVE: KPIs calculados a partir dos dados

Tom: profissional, objetivo, focado em valor de negócio.
Idioma: português brasileiro.

Você SEMPRE retorna JSON válido sem markdown.

Formato de saída:
{
  "executive_summary": "string (2-3 parágrafos)",
  "key_findings": [
    {
      "finding": "string",
      "evidence": "string",
      "importance": "high|medium|low"
    }
  ],
  "trends": [
    {
      "trend": "string",
      "direction": "up|down|stable|mixed",
      "confidence": "high|medium|low"
    }
  ],
  "anomalies": [
    {
      "description": "string",
      "records_affected": "number|null",
      "action_required": "boolean"
    }
  ],
  "recommendations": [
    {
      "action": "string",
      "priority": "high|medium|low",
      "rationale": "string"
    }
  ],
  "key_metrics": {
    "campo": "valor calculado"
  },
  "data_quality_note": "string|null",
  "confidence_level": "high|medium|low",
  "generated_at": "string (ISO 8601)"
}"""


class InsightAgent:
    """
    Produces executive summaries and actionable insights from scraped datasets.

    Example
    -------
    ::

        agent = InsightAgent(nvidia_client)
        insights = await agent.analyze(
            data=structured_data,
            context="Preços de passagens São Paulo → Rio de Janeiro",
            user_question="Qual o melhor momento para comprar?",
        )
        print(insights["executive_summary"])
        for rec in insights["recommendations"]:
            print(rec["priority"], rec["action"])
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def analyze(
        self,
        data: list[dict],
        context: str,
        user_question: str | None = None,
        focus_fields: list[str] | None = None,
    ) -> dict:
        """
        Generate full insight report from structured data.

        Parameters
        ----------
        data:
            List of clean, structured data records.
        context:
            Description of what was scraped and why.
        user_question:
            Optional specific question to answer with the analysis.
        focus_fields:
            Fields to emphasize in the analysis (e.g. ["price", "rating"]).

        Returns
        -------
        dict
            Full insight report including executive_summary, key_findings,
            trends, anomalies, recommendations, key_metrics.
        """
        log.info("insight_agent_start", records=len(data), context=context)

        if not data:
            return self._empty_insights(context)

        # Compute local stats to enrich the prompt
        local_stats = self._compute_local_stats(data, focus_fields or [])

        # Prepare prompt
        sample = data[:40]  # send up to 40 records to AI
        data_json = json.dumps(sample, ensure_ascii=False, indent=2)
        stats_json = json.dumps(local_stats, ensure_ascii=False, indent=2)

        question_section = ""
        if user_question:
            question_section = f"\nPERGUNTA ESPECÍFICA DO USUÁRIO: {user_question}\n"

        focus_section = ""
        if focus_fields:
            focus_section = f"\nFOCO DA ANÁLISE: {', '.join(focus_fields)}\n"

        prompt = (
            f"Analise estes dados e produza insights acionáveis.\n\n"
            f"Contexto: {context}\n"
            f"Total de registros: {len(data)} (mostrando amostra de {len(sample)})\n"
            f"{question_section}"
            f"{focus_section}\n"
            f"ESTATÍSTICAS CALCULADAS LOCALMENTE:\n{stats_json}\n\n"
            f"DADOS (amostra):\n{data_json}\n\n"
            f"Retorne APENAS JSON válido com o relatório completo de insights."
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_INSIGHT_SYSTEM_PROMPT,
            max_tokens=4000,
        )

        # Inject computed timestamp if not present
        if not result.get("generated_at"):
            from datetime import datetime, timezone
            result["generated_at"] = datetime.now(timezone.utc).isoformat()

        # Merge local stats into key_metrics
        result.setdefault("key_metrics", {})
        result["key_metrics"].update(local_stats.get("numeric_stats", {}))

        log.info(
            "insight_agent_done",
            findings=len(result.get("key_findings", [])),
            recommendations=len(result.get("recommendations", [])),
            confidence=result.get("confidence_level"),
        )
        return result

    async def quick_summary(self, data: list[dict], context: str) -> str:
        """
        Generate a brief 3-5 sentence natural language summary.

        Faster and cheaper than ``analyze()`` — good for previews.

        Returns
        -------
        str
            Plain text summary in Brazilian Portuguese.
        """
        sample = data[:20]
        data_json = json.dumps(sample, ensure_ascii=False)

        prompt = (
            f"Resuma em 3-5 frases os principais insights destes dados.\n\n"
            f"Contexto: {context}\n"
            f"Total de registros: {len(data)}\n\n"
            f"DADOS:\n{data_json}\n\n"
            f"Retorne JSON: {{ \"summary\": \"texto do resumo\" }}"
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_INSIGHT_SYSTEM_PROMPT,
            max_tokens=500,
        )
        return result.get("summary", "Resumo indisponível.")

    async def compare_datasets(
        self,
        dataset_a: list[dict],
        dataset_b: list[dict],
        context_a: str,
        context_b: str,
    ) -> dict:
        """
        Compare two datasets and highlight differences.

        Useful for tracking changes over time (price monitoring, news trends, etc.).

        Returns
        -------
        dict
            ``{"comparison_summary": str, "changes": [...], "recommendation": str}``
        """
        stats_a = self._compute_local_stats(dataset_a[:30], [])
        stats_b = self._compute_local_stats(dataset_b[:30], [])

        prompt = (
            f"Compare estes dois datasets e destaque as diferenças mais relevantes.\n\n"
            f"DATASET A — {context_a}:\n"
            f"Registros: {len(dataset_a)}\n"
            f"Stats: {json.dumps(stats_a, ensure_ascii=False)}\n"
            f"Amostra: {json.dumps(dataset_a[:10], ensure_ascii=False)}\n\n"
            f"DATASET B — {context_b}:\n"
            f"Registros: {len(dataset_b)}\n"
            f"Stats: {json.dumps(stats_b, ensure_ascii=False)}\n"
            f"Amostra: {json.dumps(dataset_b[:10], ensure_ascii=False)}\n\n"
            f"Retorne JSON: {{"
            f'"comparison_summary": "string", '
            f'"changes": [{{"field": "...", "change": "...", "direction": "up|down|stable"}}], '
            f'"recommendation": "string"'
            f"}}"
        )

        return await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_INSIGHT_SYSTEM_PROMPT,
            max_tokens=1500,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_local_stats(data: list[dict], focus_fields: list[str]) -> dict:
        """Compute basic statistics locally to enrich the AI prompt."""
        if not data:
            return {}

        numeric_stats: dict[str, Any] = {}
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())

        numeric_fields = focus_fields or list(all_fields)

        for field in numeric_fields:
            values = [r[field] for r in data if field in r and isinstance(r[field], (int, float))]
            if len(values) >= 2:
                numeric_stats[field] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": round(statistics.mean(values), 2),
                    "median": round(statistics.median(values), 2),
                    "count": len(values),
                }

        null_rates: dict[str, str] = {}
        for field in all_fields:
            total = len(data)
            nulls = sum(1 for r in data if r.get(field) is None or r.get(field) == "")
            rate = round(nulls / total * 100, 1)
            if rate > 0:
                null_rates[field] = f"{rate}%"

        return {
            "total_records": len(data),
            "fields_available": sorted(all_fields),
            "numeric_stats": numeric_stats,
            "null_rates": null_rates,
        }

    @staticmethod
    def _empty_insights(context: str) -> dict:
        from datetime import datetime, timezone
        return {
            "executive_summary": f"Nenhum dado disponível para análise. Contexto: {context}",
            "key_findings": [],
            "trends": [],
            "anomalies": [],
            "recommendations": [
                {
                    "action": "Verificar se o scraper está funcionando corretamente.",
                    "priority": "high",
                    "rationale": "Dataset vazio.",
                }
            ],
            "key_metrics": {},
            "data_quality_note": "Dataset vazio.",
            "confidence_level": "low",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
