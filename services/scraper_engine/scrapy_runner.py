"""
ScrapyRunner — execução programática de spiders Scrapy via CrawlerRunner.

Integra Twisted com asyncio usando asyncio.get_event_loop() e
defer.inlineCallbacks para que o caller possa usar await normalmente.
"""

import asyncio
import logging
from typing import Any

import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from twisted.internet import asyncioreactor

# Instala o reactor asyncio antes de qualquer import do reactor padrão.
try:
    asyncioreactor.install()
except Exception:
    pass  # Já instalado ou em ambiente que não suporta.

from twisted.internet import defer, reactor as _reactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spider genérico configurável via parâmetros
# ---------------------------------------------------------------------------

class DynamicSpider(scrapy.Spider):
    """
    Spider genérico que aceita URL e seletores CSS/XPath via construtor.

    Parâmetros
    ----------
    url : str
        URL alvo do scraping.
    selectors : dict, optional
        Mapeamento {campo: seletor}. Seletores começando com "//" são XPath;
        demais são CSS.
    custom_settings : dict, optional
        Configurações extras do Scrapy para este spider.
    """

    name = "dynamic_spider"

    def __init__(
        self,
        url: str,
        selectors: dict | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        self.selectors = selectors or {}

    def parse(self, response: scrapy.http.Response):  # type: ignore[override]
        item: dict = {}

        # Aplica seletores configurados
        for field, selector in self.selectors.items():
            if selector.startswith("//"):
                item[field] = response.xpath(selector).getall()
            else:
                item[field] = response.css(selector).getall()

        # Auto-detecção quando não há seletores
        if not self.selectors:
            tables = self._extract_tables(response)
            if tables:
                item["tables"] = tables
            else:
                item["text_content"] = response.css("body *::text").getall()[:500]
            # Metadados básicos sempre presentes
            item["url"] = response.url
            item["title"] = response.css("title::text").get("")
            item["status"] = response.status

        yield item

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_tables(self, response: scrapy.http.Response) -> list[dict]:
        """Extrai todas as tabelas HTML da resposta como lista de dicts."""
        tables: list[dict] = []
        for table in response.css("table"):
            headers = table.css("th::text").getall()
            rows: list = []
            for tr in table.css("tbody tr, tr"):
                cells = tr.css("td::text, td *::text").getall()
                if not cells:
                    continue
                if headers:
                    rows.append(dict(zip(headers, cells)))
                else:
                    rows.append(cells)
            if rows:
                tables.append({"headers": headers, "rows": rows})
        return tables


# ---------------------------------------------------------------------------
# Runner assíncrono
# ---------------------------------------------------------------------------

class ScrapyRunner:
    """
    Executa um DynamicSpider (ou qualquer spider) de forma assíncrona,
    retornando os itens coletados como lista de dicts.
    """

    def __init__(self) -> None:
        configure_logging(install_root_handler=False)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def run(
        self,
        url: str,
        selectors: dict | None = None,
        settings_override: dict | None = None,
        spider_cls: type | None = None,
    ) -> list[dict]:
        """
        Executa o spider e retorna lista de itens.

        Parâmetros
        ----------
        url : str
            URL alvo.
        selectors : dict, optional
            Seletores CSS/XPath para extração.
        settings_override : dict, optional
            Sobrescreve configurações padrão do Scrapy.
        spider_cls : type, optional
            Classe spider customizada. Padrão: DynamicSpider.

        Retorno
        -------
        list[dict]
            Itens scraped normalizados.
        """
        settings = self._build_settings(settings_override or {})
        runner = CrawlerRunner(settings)
        items: list[dict] = []

        spider_cls = spider_cls or DynamicSpider

        logger.info("ScrapyRunner.run() | url=%s | selectors=%s", url, selectors)

        await self._crawl(runner, spider_cls, items, url=url, selectors=selectors)

        logger.info("ScrapyRunner.run() | coletados=%d itens", len(items))
        return items

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_settings(self, override: dict) -> Any:
        settings = get_project_settings()
        defaults = {
            "ROBOTSTXT_OBEY": False,
            "COOKIES_ENABLED": True,
            "DOWNLOAD_TIMEOUT": 30,
            "RETRY_TIMES": 3,
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
            "AUTOTHROTTLE_ENABLED": True,
            "AUTOTHROTTLE_START_DELAY": 1,
            "AUTOTHROTTLE_MAX_DELAY": 10,
            "DEFAULT_REQUEST_HEADERS": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
            "LOG_LEVEL": "WARNING",
        }
        defaults.update(override)
        for k, v in defaults.items():
            settings.set(k, v)
        return settings

    async def _crawl(
        self,
        runner: CrawlerRunner,
        spider_cls: type,
        items: list,
        **spider_kwargs: Any,
    ) -> None:
        """
        Executa o crawler dentro do event loop asyncio atual,
        bridging Twisted Deferred → asyncio Future.
        """
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        def _item_scraped(item, response, spider):  # noqa: ANN001
            items.append(dict(item))

        def _crawl_done(result):  # noqa: ANN001
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, items)

        def _crawl_failed(failure):  # noqa: ANN001
            exc = failure.value
            logger.error("ScrapyRunner crawl failed: %s", exc)
            if not future.done():
                loop.call_soon_threadsafe(future.set_exception, exc)

        crawler = runner.create_crawler(spider_cls)
        crawler.signals.connect(_item_scraped, signal=scrapy.signals.item_scraped)

        d = runner.crawl(crawler, **spider_kwargs)
        d.addCallback(_crawl_done)
        d.addErrback(_crawl_failed)

        await future
