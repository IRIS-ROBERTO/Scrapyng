"""
SelectorTester — testa seletores CSS/XPath em uma URL sem rodar um spider completo.

Faz um fetch leve (httpx) da URL e aplica os seletores via parsel
(mesma biblioteca usada pelo Scrapy internamente), devolvendo resultados
e métricas de qualidade de cada seletor.
"""

import logging
import time
from typing import Any

import httpx
from parsel import Selector

logger = logging.getLogger(__name__)

# Timeout padrão para o fetch (segundos)
_FETCH_TIMEOUT = 20

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
}


class SelectorTester:
    """
    Testa seletores CSS e XPath contra uma URL sem a sobrecarga de um spider completo.

    Exemplo de uso
    --------------
    tester = SelectorTester()
    result = await tester.test(
        url="https://example.com",
        selectors={"titulo": "h1::text", "links": "//a/@href"},
    )
    """

    def __init__(self, timeout: int = _FETCH_TIMEOUT) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def test(
        self,
        url: str,
        selectors: dict[str, str],
        follow_redirects: bool = True,
    ) -> dict:
        """
        Faz o fetch da URL e aplica cada seletor, retornando resultados e métricas.

        Parâmetros
        ----------
        url : str
            URL alvo (deve ser página HTML estática ou server-side rendered).
        selectors : dict
            {nome_campo: seletor_css_ou_xpath}
        follow_redirects : bool
            Seguir redirects HTTP (padrão True).

        Retorno
        -------
        dict com:
            - url: URL final (após redirects)
            - status: HTTP status code
            - fetch_time_ms: tempo de fetch em ms
            - results: {campo: {matches: list, count: int, quality: str}}
            - errors: lista de erros por campo
            - html_preview: primeiros 500 chars do HTML (para debug)
        """
        logger.info("SelectorTester.test() | url=%s | campos=%s", url, list(selectors.keys()))

        html, status, final_url, fetch_ms = await self._fetch(url, follow_redirects)

        if not html:
            return {
                "url": final_url,
                "status": status,
                "fetch_time_ms": fetch_ms,
                "results": {},
                "errors": ["Falha ao obter HTML da URL"],
                "html_preview": "",
            }

        sel = Selector(text=html)
        results: dict = {}
        errors: list[str] = []

        for field, selector in selectors.items():
            field_result = self._apply_selector(sel, field, selector)
            if "error" in field_result:
                errors.append(f"{field}: {field_result['error']}")
            results[field] = field_result

        return {
            "url": final_url,
            "status": status,
            "fetch_time_ms": fetch_ms,
            "results": results,
            "errors": errors,
            "html_preview": html[:500],
        }

    async def test_single(
        self,
        url: str,
        selector: str,
        field_name: str = "result",
    ) -> dict:
        """
        Testa um único seletor. Atalho para test() com um campo.
        """
        return await self.test(url, {field_name: selector})

    def suggest_selectors(self, html: str) -> dict[str, str]:
        """
        Analisa o HTML e sugere seletores para campos comuns:
        título, parágrafos, links, preços, imagens.

        Parâmetros
        ----------
        html : str
            HTML cru da página.

        Retorno
        -------
        dict {campo: seletor_sugerido}
        """
        sel = Selector(text=html)
        suggestions: dict[str, str] = {}

        # Título
        if sel.css("h1::text").get():
            suggestions["title"] = "h1::text"
        elif sel.css("title::text").get():
            suggestions["title"] = "title::text"

        # Preço (padrão comum: elementos com classe contendo "price")
        for price_cls in ("price", "preco", "valor", "cost", "amount"):
            if sel.css(f"[class*='{price_cls}']::text").getall():
                suggestions["price"] = f"[class*='{price_cls}']::text"
                break

        # Parágrafos
        paras = sel.css("article p::text, main p::text, .content p::text").getall()
        if paras:
            suggestions["paragraphs"] = "article p::text, main p::text"

        # Links internos
        links = sel.css("a[href]::attr(href)").getall()
        if links:
            suggestions["links"] = "a::attr(href)"

        # Imagens
        imgs = sel.css("img::attr(src)").getall()
        if imgs:
            suggestions["images"] = "img::attr(src)"

        # Tabelas
        if sel.css("table"):
            suggestions["tables"] = "table"

        return suggestions

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _fetch(
        self, url: str, follow_redirects: bool
    ) -> tuple[str, int, str, float]:
        """Retorna (html, status, final_url, fetch_time_ms)."""
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(
                headers=_DEFAULT_HEADERS,
                timeout=self.timeout,
                follow_redirects=follow_redirects,
            ) as client:
                resp = await client.get(url)
                fetch_ms = round((time.monotonic() - t0) * 1000, 2)
                return resp.text, resp.status_code, str(resp.url), fetch_ms
        except httpx.TimeoutException:
            logger.error("Timeout ao buscar %s", url)
            return "", 0, url, round((time.monotonic() - t0) * 1000, 2)
        except Exception as exc:
            logger.error("Erro ao buscar %s: %s", url, exc)
            return "", 0, url, round((time.monotonic() - t0) * 1000, 2)

    def _apply_selector(self, sel: Selector, field: str, selector: str) -> dict:
        """Aplica um seletor CSS ou XPath e retorna métricas."""
        try:
            if selector.startswith("//") or selector.startswith("(//"):
                matches = sel.xpath(selector).getall()
            else:
                matches = sel.css(selector).getall()

            matches = [m.strip() for m in matches if m.strip()]
            quality = self._quality_label(matches)

            return {
                "matches": matches[:50],  # limite para não estourar payload
                "count": len(matches),
                "quality": quality,
                "selector_type": "xpath" if selector.startswith("//") else "css",
            }
        except Exception as exc:
            return {"error": str(exc), "matches": [], "count": 0, "quality": "error"}

    @staticmethod
    def _quality_label(matches: list) -> str:
        """Classifica a qualidade do seletor pelo número de matches."""
        n = len(matches)
        if n == 0:
            return "empty"
        if n == 1:
            return "good"
        if n <= 20:
            return "good"
        if n <= 100:
            return "ok"
        return "too_many"
