"""
PlaywrightRunner — scraping de páginas JS-rendered via Playwright async.

Funcionalidades:
- Stealth mode para evitar detecção de bot
- Scroll automático para lazy-load
- Screenshot automático para debugging
- Suporte a networkidle, selector ou tempo como critério de wait
- Extração automática (tabelas, cards, listas, texto estruturado)
"""

import asyncio
import base64
import hashlib
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stealth JS — injeta overrides básicos de fingerprint no browser
# ---------------------------------------------------------------------------

_STEALTH_SCRIPT = """
() => {
    // Oculta webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Simula plugins normais
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // Simula linguagens comuns
    Object.defineProperty(navigator, 'languages', {
        get: () => ['pt-BR', 'pt', 'en-US', 'en'],
    });

    // Chrome runtime fake
    window.chrome = { runtime: {} };

    // Remove sinais de headless
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
}
"""


class PlaywrightRunner:
    """
    Runner assíncrono baseado em Playwright para páginas com JavaScript pesado.
    """

    DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        headless: bool = True,
        proxy: str | None = None,
    ) -> None:
        self.headless = headless
        self.proxy = proxy

    # ------------------------------------------------------------------
    # API pública principal
    # ------------------------------------------------------------------

    async def run(
        self,
        url: str,
        selectors: dict | None = None,
        wait_for: str = "networkidle",
        timeout: int = 30000,
        stealth: bool = True,
        screenshot: bool = False,
        scroll: bool = True,
    ) -> dict:
        """
        Scraping com Playwright.

        Parâmetros
        ----------
        url : str
            URL alvo.
        selectors : dict, optional
            {campo: seletor CSS ou XPath}. Se None, usa auto_extract().
        wait_for : str
            Critério de espera: "networkidle", "domcontentloaded", "load",
            seletor CSS específico (começa com "." ou "#") ou "Ns" (ex: "2s").
        timeout : int
            Timeout em ms (padrão 30000).
        stealth : bool
            Ativa stealth mode (padrão True).
        screenshot : bool
            Captura screenshot e inclui no resultado como base64.
        scroll : bool
            Faz scroll automático para disparar lazy-load.

        Retorno
        -------
        dict com campos extraídos + metadados (url, status, title).
        """
        logger.info("PlaywrightRunner.run() | url=%s | wait_for=%s", url, wait_for)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
                proxy={"server": self.proxy} if self.proxy else None,
            )
            context = await self._build_context(browser, stealth)
            page = await context.new_page()

            if stealth:
                await page.add_init_script(_STEALTH_SCRIPT)

            result: dict = {}

            try:
                response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                result["status"] = response.status if response else 0

                await self._wait(page, wait_for, timeout)

                if scroll:
                    await self._auto_scroll(page)

                result["url"] = page.url
                result["title"] = await page.title()

                if selectors:
                    extracted = await self._apply_selectors(page, selectors)
                    result.update(extracted)
                else:
                    auto = await self.auto_extract(url, _page=page)
                    result.update(auto)

                if screenshot:
                    result["screenshot_b64"] = await self._take_screenshot(page)

            except Exception as exc:
                logger.error("PlaywrightRunner.run() error: %s", exc)
                result["error"] = str(exc)
            finally:
                await browser.close()

        return result

    async def extract_with_ai_selectors(
        self,
        url: str,
        ai_selectors: dict,
        timeout: int = 30000,
    ) -> dict:
        """
        Usa seletores gerados pela IA (campo → seletor CSS/XPath).
        Idêntico ao run() com selectors=ai_selectors e stealth=True.
        """
        return await self.run(url, selectors=ai_selectors, timeout=timeout, stealth=True)

    async def auto_extract(
        self,
        url: str,
        timeout: int = 30000,
        _page: "Page | None" = None,
    ) -> dict:
        """
        Extração automática sem seletores.
        Detecta e extrai na ordem:
        1. Tabelas HTML
        2. Cards/listas repetitivos (article, .card, li com filhos)
        3. Metadados estruturados (og:*, JSON-LD)
        4. Texto do body

        Se _page for fornecido (uso interno), não abre novo browser.
        """
        if _page is not None:
            return await self._auto_extract_page(_page)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            context = await self._build_context(browser, stealth=True)
            page = await context.new_page()
            await page.add_init_script(_STEALTH_SCRIPT)
            try:
                await page.goto(url, timeout=timeout, wait_until="networkidle")
                await self._auto_scroll(page)
                result = await self._auto_extract_page(page)
                result["url"] = page.url
                result["title"] = await page.title()
            finally:
                await browser.close()
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _build_context(self, browser: Any, stealth: bool) -> "BrowserContext":
        kwargs: dict = {
            "viewport": self.DEFAULT_VIEWPORT,
            "user_agent": self.DEFAULT_USER_AGENT,
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "extra_http_headers": {
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            },
        }
        if stealth:
            kwargs["java_script_enabled"] = True
        return await browser.new_context(**kwargs)

    async def _wait(self, page: "Page", wait_for: str, timeout: int) -> None:
        """Aguarda pelo critério especificado."""
        if wait_for in ("networkidle", "domcontentloaded", "load"):
            await page.wait_for_load_state(wait_for, timeout=timeout)
        elif re.match(r"^\d+(\.\d+)?s$", wait_for):
            secs = float(wait_for[:-1])
            await asyncio.sleep(secs)
        elif wait_for:
            try:
                await page.wait_for_selector(wait_for, timeout=timeout)
            except Exception:
                logger.warning("Selector '%s' não encontrado; continuando.", wait_for)

    async def _auto_scroll(self, page: "Page") -> None:
        """Scroll suave para o fundo da página para acionar lazy-load."""
        await page.evaluate(
            """async () => {
                await new Promise((resolve) => {
                    let total = 0;
                    const step = 300;
                    const delay = 100;
                    const timer = setInterval(() => {
                        window.scrollBy(0, step);
                        total += step;
                        if (total >= document.body.scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, delay);
                    // Timeout de segurança: 8 segundos
                    setTimeout(() => { clearInterval(timer); resolve(); }, 8000);
                });
            }"""
        )

    async def _apply_selectors(self, page: "Page", selectors: dict) -> dict:
        """Aplica seletores CSS/XPath e retorna dict com os valores."""
        result: dict = {}
        for field, selector in selectors.items():
            try:
                if selector.startswith("//"):
                    # XPath via evaluate
                    values = await page.evaluate(
                        """(xpath) => {
                            const r = document.evaluate(
                                xpath, document, null,
                                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                            );
                            const out = [];
                            for (let i = 0; i < r.snapshotLength; i++) {
                                out.push(r.snapshotItem(i).textContent.trim());
                            }
                            return out;
                        }""",
                        selector,
                    )
                else:
                    elements = await page.query_selector_all(selector)
                    values = []
                    for el in elements:
                        txt = await el.inner_text()
                        values.append(txt.strip())
                result[field] = values
            except Exception as exc:
                logger.warning("Seletor '%s' falhou: %s", selector, exc)
                result[field] = []
        return result

    async def _auto_extract_page(self, page: "Page") -> dict:
        """Extração automática a partir de um objeto Page já aberto."""
        result: dict = {}

        # 1. Tabelas
        tables = await self._extract_tables(page)
        if tables:
            result["tables"] = tables

        # 2. Cards/listas repetitivos
        cards = await self._extract_cards(page)
        if cards:
            result["cards"] = cards

        # 3. Metadados estruturados
        meta = await self._extract_meta(page)
        if meta:
            result["meta"] = meta

        # 4. Imagens relevantes
        images = await self._extract_images(page)
        if images:
            result["images"] = images

        # 5. Texto do body (fallback)
        if not tables and not cards:
            result["text_content"] = await page.evaluate(
                "() => document.body.innerText.slice(0, 5000)"
            )

        return result

    async def _extract_tables(self, page: "Page") -> list[dict]:
        return await page.evaluate(
            """() => {
                const tables = [];
                document.querySelectorAll('table').forEach(table => {
                    const headers = [...table.querySelectorAll('th')].map(th => th.innerText.trim());
                    const rows = [];
                    table.querySelectorAll('tbody tr, tr').forEach(tr => {
                        const cells = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
                        if (cells.length === 0) return;
                        if (headers.length > 0) {
                            const row = {};
                            headers.forEach((h, i) => { row[h || i] = cells[i] || ''; });
                            rows.push(row);
                        } else {
                            rows.push(cells);
                        }
                    });
                    if (rows.length > 0) tables.push({ headers, rows });
                });
                return tables;
            }"""
        )

    async def _extract_cards(self, page: "Page") -> list[dict]:
        """Detecta e extrai cards/listas repetitivos (article, .card, li com sub-elementos)."""
        return await page.evaluate(
            """() => {
                const candidates = [
                    ...document.querySelectorAll('article'),
                    ...document.querySelectorAll('[class*="card"]'),
                    ...document.querySelectorAll('[class*="item"]'),
                    ...document.querySelectorAll('li[class]'),
                ];
                if (candidates.length < 3) return [];
                return candidates.slice(0, 100).map(el => ({
                    text: el.innerText.trim().slice(0, 500),
                    href: el.querySelector('a')?.href || null,
                    img: el.querySelector('img')?.src || null,
                })).filter(c => c.text.length > 10);
            }"""
        )

    async def _extract_meta(self, page: "Page") -> dict:
        """Extrai Open Graph, Twitter Card e JSON-LD."""
        return await page.evaluate(
            """() => {
                const meta = {};
                document.querySelectorAll('meta').forEach(m => {
                    const prop = m.getAttribute('property') || m.getAttribute('name') || '';
                    if ((prop.startsWith('og:') || prop.startsWith('twitter:')) && m.content) {
                        meta[prop] = m.content;
                    }
                });
                document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                    try {
                        meta['json_ld'] = JSON.parse(s.textContent);
                    } catch(e) {}
                });
                return meta;
            }"""
        )

    async def _extract_images(self, page: "Page") -> list[str]:
        """Extrai URLs de imagens com área > 5000px² (evita ícones)."""
        return await page.evaluate(
            """() => {
                return [...document.querySelectorAll('img')]
                    .filter(img => img.naturalWidth * img.naturalHeight > 5000)
                    .map(img => img.src)
                    .filter(src => src && !src.startsWith('data:'))
                    .slice(0, 20);
            }"""
        )

    async def _take_screenshot(self, page: "Page") -> str:
        """Captura screenshot e retorna como string base64."""
        buf = await page.screenshot(full_page=True, type="jpeg", quality=70)
        return base64.b64encode(buf).decode()
