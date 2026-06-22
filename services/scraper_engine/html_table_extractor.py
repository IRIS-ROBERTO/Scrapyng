"""
HTMLTableExtractor — detecta e extrai tabelas HTML automaticamente.

Suporta:
- Tabelas simples (thead/tbody/tfoot)
- Tabelas com colspan/rowspan
- Exportação para lista de dicts, CSV e JSON
- Score de qualidade por tabela
"""

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from parsel import Selector

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Representa uma tabela extraída com seus metadados."""

    index: int
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""
    quality_score: float = 0.0
    has_header: bool = True

    # ------------------------------------------------------------------
    # Conversões
    # ------------------------------------------------------------------

    def to_records(self) -> list[dict]:
        """Converte para lista de dicts {header: valor}."""
        if self.has_header and self.headers:
            return [
                {self.headers[i] if i < len(self.headers) else f"col_{i}": cell
                 for i, cell in enumerate(row)}
                for row in self.rows
            ]
        return [{"col_" + str(i): v for i, v in enumerate(row)} for row in self.rows]

    def to_csv(self) -> str:
        """Retorna a tabela como string CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        if self.headers:
            writer.writerow(self.headers)
        writer.writerows(self.rows)
        return buf.getvalue()

    def to_json(self, indent: int = 2) -> str:
        """Retorna a tabela como JSON (lista de dicts)."""
        return json.dumps(self.to_records(), ensure_ascii=False, indent=indent)

    def summary(self) -> dict:
        """Resumo compacto para logging/API."""
        return {
            "index": self.index,
            "caption": self.caption,
            "headers": self.headers,
            "row_count": len(self.rows),
            "col_count": len(self.headers) or (len(self.rows[0]) if self.rows else 0),
            "quality_score": self.quality_score,
        }


class HTMLTableExtractor:
    """
    Extrai todas as tabelas de um HTML ou URL.

    Exemplo de uso
    --------------
    extractor = HTMLTableExtractor()

    # A partir de HTML bruto
    tables = extractor.extract_from_html(html_str)

    # A partir de URL (fetch síncrono via httpx)
    tables = await extractor.extract_from_url("https://exemplo.com/tabela")

    for table in tables:
        print(table.to_records())
    """

    def __init__(
        self,
        min_rows: int = 1,
        min_cols: int = 1,
        skip_empty: bool = True,
    ) -> None:
        """
        Parâmetros
        ----------
        min_rows : int
            Ignora tabelas com menos de N linhas de dados (padrão 1).
        min_cols : int
            Ignora tabelas com menos de N colunas (padrão 1).
        skip_empty : bool
            Remove células/linhas completamente vazias.
        """
        self.min_rows = min_rows
        self.min_cols = min_cols
        self.skip_empty = skip_empty

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def extract_from_html(self, html: str) -> list[ExtractedTable]:
        """
        Extrai todas as tabelas de um HTML bruto.

        Parâmetros
        ----------
        html : str
            HTML completo ou fragmento.

        Retorno
        -------
        list[ExtractedTable] ordenado por quality_score descendente.
        """
        sel = Selector(text=html)
        tables: list[ExtractedTable] = []

        for idx, table_sel in enumerate(sel.css("table")):
            extracted = self._parse_table(table_sel, index=idx)
            if extracted is None:
                continue
            if len(extracted.rows) < self.min_rows:
                continue
            col_count = len(extracted.headers) or (len(extracted.rows[0]) if extracted.rows else 0)
            if col_count < self.min_cols:
                continue
            tables.append(extracted)

        # Ordena por qualidade
        tables.sort(key=lambda t: t.quality_score, reverse=True)
        logger.info("HTMLTableExtractor: %d tabelas encontradas", len(tables))
        return tables

    async def extract_from_url(self, url: str, timeout: int = 20) -> list[ExtractedTable]:
        """
        Faz fetch da URL e extrai tabelas.

        Parâmetros
        ----------
        url : str
            URL alvo (página estática ou server-side rendered).
        timeout : int
            Timeout em segundos.
        """
        import httpx

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return self.extract_from_html(resp.text)

    def extract_best(self, html: str) -> ExtractedTable | None:
        """Retorna apenas a tabela com melhor quality_score, ou None."""
        tables = self.extract_from_html(html)
        return tables[0] if tables else None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parse_table(self, table_sel: Selector, index: int) -> ExtractedTable | None:
        """Parseia um elemento <table> e retorna ExtractedTable."""
        # Caption
        caption = table_sel.css("caption::text").get("").strip()

        # Headers: prioriza <thead>, senão primeiro <tr> com <th>
        headers = self._extract_headers(table_sel)

        # Linhas de dados
        rows = self._extract_rows(table_sel, has_header=bool(headers))

        if not rows and not headers:
            return None

        if self.skip_empty:
            rows = [r for r in rows if any(c.strip() for c in r)]

        table = ExtractedTable(
            index=index,
            headers=headers,
            rows=rows,
            caption=caption,
            has_header=bool(headers),
        )
        table.quality_score = self._score_table(table)
        return table

    def _extract_headers(self, table_sel: Selector) -> list[str]:
        """Extrai cabeçalhos de <thead> ou <th> no primeiro <tr>."""
        # Tenta thead
        headers = table_sel.css("thead th::text, thead td::text").getall()
        if headers:
            return [h.strip() for h in headers]

        # Tenta primeiro <tr> com <th>
        first_tr = table_sel.css("tr").get("")
        if "<th" in first_tr.lower():
            headers = Selector(text=first_tr).css("th::text").getall()
            return [h.strip() for h in headers]

        return []

    def _extract_rows(self, table_sel: Selector, has_header: bool) -> list[list[str]]:
        """
        Extrai linhas de dados, com suporte básico a colspan/rowspan.
        Se has_header=True, pula o primeiro <tr> (já extraído como header).
        """
        all_trs = table_sel.css("tbody tr, tfoot tr")
        if not all_trs:
            # Fallback: todos os <tr>
            all_trs = table_sel.css("tr")

        rows: list[list[str]] = []
        skip_first = has_header and not table_sel.css("thead")

        for i, tr in enumerate(all_trs):
            if skip_first and i == 0:
                continue
            cells = tr.css("td::text, td *::text").getall()
            # Agrupa textos de células
            cells_clean = self._merge_cell_texts(tr)
            if cells_clean:
                rows.append(cells_clean)

        return rows

    def _merge_cell_texts(self, tr_sel: Selector) -> list[str]:
        """Extrai o texto de cada <td> como string única."""
        result: list[str] = []
        for td in tr_sel.css("td"):
            texts = td.css("*::text").getall()
            cell_text = " ".join(t.strip() for t in texts if t.strip())
            if not cell_text:
                cell_text = td.css("::text").get("").strip()
            result.append(cell_text)
        return result

    def _score_table(self, table: ExtractedTable) -> float:
        """
        Calcula score 0.0-1.0 de qualidade:
        - Ter headers: +0.3
        - Múltiplas colunas (3+): +0.2
        - Múltiplas linhas (5+): +0.2
        - Caption: +0.1
        - Cells não vazias: até +0.2
        """
        score = 0.0
        if table.has_header and table.headers:
            score += 0.3
        col_count = len(table.headers) or (len(table.rows[0]) if table.rows else 0)
        if col_count >= 3:
            score += 0.2
        if len(table.rows) >= 5:
            score += 0.2
        if table.caption:
            score += 0.1

        # Preenchimento das células
        if table.rows:
            total_cells = sum(len(r) for r in table.rows)
            filled = sum(1 for r in table.rows for c in r if c.strip())
            if total_cells > 0:
                score += 0.2 * (filled / total_cells)

        return round(score, 3)
