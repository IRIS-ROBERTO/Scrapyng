"""
Gera relatório executivo em Markdown a partir dos dados extraídos.
Pode ser convertido para PDF externamente (ex: pandoc, weasyprint).
"""
from datetime import datetime
from typing import Any
import statistics


class ReportExporter:
    def export_markdown(
        self,
        data: list[dict],
        job_name: str = "Scraping Job",
        quality_result: dict | None = None,
        insights: str | None = None,
    ) -> str:
        now = datetime.now().strftime("%d/%m/%Y às %H:%M")
        lines = [
            f"# Relatório de Scraping — {job_name}",
            f"*Gerado em {now} pela WebScrapy AI Platform*",
            "",
            "---",
            "",
            "## Resumo Executivo",
            "",
            f"- **Total de registros coletados:** {len(data)}",
        ]

        if quality_result:
            lines += [
                f"- **Score de Qualidade:** {quality_result.get('score', 'N/A')}/100 (Grade {quality_result.get('grade', 'N/A')})",
                f"- **Itens válidos:** {quality_result.get('items_count', len(data))}",
            ]

        if data:
            fields = list(data[0].keys())
            lines += [
                f"- **Campos extraídos:** {', '.join(fields)}",
                "",
            ]

        if insights:
            lines += [
                "## Insights da IA",
                "",
                insights,
                "",
            ]

        if quality_result and quality_result.get("issues"):
            lines += [
                "## Alertas de Qualidade",
                "",
            ]
            for issue in quality_result["issues"][:10]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

        # Amostra de dados em tabela Markdown
        if data:
            sample = data[:20]
            fields = list(sample[0].keys())[:8]  # max 8 colunas

            lines += [
                "## Amostra de Dados (20 primeiros registros)",
                "",
                "| " + " | ".join(f[:20] for f in fields) + " |",
                "| " + " | ".join(["---"] * len(fields)) + " |",
            ]
            for item in sample:
                row_vals = []
                for f in fields:
                    val = str(item.get(f, ""))[:30].replace("|", "\\|")
                    row_vals.append(val)
                lines.append("| " + " | ".join(row_vals) + " |")

            lines.append("")

        lines += [
            "---",
            "*Relatório gerado automaticamente pela WebScrapy AI Platform*",
        ]

        return "\n".join(lines)

    def export_string(self, data: list[dict], **kwargs) -> str:
        return self.export_markdown(data, **kwargs)

    def export(self, data: list[dict], filename: str | None = None, **kwargs) -> str:
        content = self.export_markdown(data, **kwargs)
        path = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
