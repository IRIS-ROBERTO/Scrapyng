"""
Scrapy spider and Playwright script generator.

Generates complete, runnable Python scraping code from a page analysis
and a list of desired fields, using NVIDIA NIM.
"""

from __future__ import annotations

import structlog

from .nvidia_client import NvidiaClient
from .prompts.scraper_generation import SCRAPER_SYSTEM_PROMPT, build_scraper_prompt

log = structlog.get_logger(__name__)


class ScraperGenerator:
    """
    Generates complete scraper code (Scrapy spider and/or Playwright script).

    Example
    -------
    ::

        gen = ScraperGenerator(nvidia_client)
        result = await gen.generate(
            url="https://books.toscrape.com",
            page_analysis=analysis,
            target_fields=["title", "price", "availability"],
            spider_name="books_spider",
        )
        print(result["scrapy_spider"])   # full Python code
        print(result["run_command"])     # e.g. "scrapy runspider books_spider.py -o output.json"
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def generate(
        self,
        url: str,
        page_analysis: dict,
        target_fields: list[str],
        spider_name: str = "auto_spider",
        max_pages: int = 10,
        output_format: str = "json",
    ) -> dict:
        """
        Generate scraper code for the given page.

        Parameters
        ----------
        url:
            Starting URL for the scraper.
        page_analysis:
            Output from ``PageAnalyzer.analyze()``.
        target_fields:
            List of field names to extract.
        spider_name:
            Python identifier for the generated spider class.
        max_pages:
            Maximum pages to crawl.
        output_format:
            Output format hint for generated spider (json, csv, jsonlines).

        Returns
        -------
        dict
            - ``strategy``: scrapy | playwright | scrapy+playwright
            - ``scrapy_spider``: full Python spider code (or None)
            - ``playwright_script``: full async Python script (or None)
            - ``requirements``: list of pip packages
            - ``run_command``: CLI command to execute
            - ``estimated_items_per_minute``: rough estimate
            - ``notes``: caveats and recommendations
        """
        log.info(
            "scraper_generator_start",
            url=url,
            spider_name=spider_name,
            fields=target_fields,
        )

        # Inject output format into page_analysis for context
        enriched_analysis = {**page_analysis, "_output_format": output_format}

        user_message = build_scraper_prompt(
            url=url,
            page_analysis=enriched_analysis,
            target_fields=target_fields,
            spider_name=spider_name,
            max_pages=max_pages,
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SCRAPER_SYSTEM_PROMPT,
            max_tokens=6000,
        )

        strategy = result.get("strategy", "scrapy")
        log.info(
            "scraper_generator_done",
            url=url,
            spider_name=spider_name,
            strategy=strategy,
            has_scrapy=bool(result.get("scrapy_spider")),
            has_playwright=bool(result.get("playwright_script")),
        )
        return result

    async def generate_playwright_only(
        self,
        url: str,
        page_analysis: dict,
        target_fields: list[str],
        output_file: str = "output.json",
    ) -> dict:
        """
        Generate a Playwright-only async Python script.

        Use this when the page requires JavaScript rendering and Scrapy alone
        is insufficient.

        Returns
        -------
        dict
            Same structure as ``generate()``, with strategy forced to
            ``"playwright"`` and ``playwright_script`` populated.
        """
        import json

        analysis_json = json.dumps(page_analysis, ensure_ascii=False, indent=2)
        fields_str = ", ".join(target_fields)

        user_message = (
            f"Gere APENAS um script Python assíncrono com Playwright para extrair dados desta página.\n\n"
            f"URL: {url}\n"
            f"Arquivo de saída: {output_file}\n"
            f"Campos a extrair: {fields_str}\n\n"
            f"Análise da página:\n{analysis_json}\n\n"
            f"Use playwright.async_api. Inclua waits adequados para conteúdo dinâmico.\n"
            f"O script deve salvar os dados em {output_file} ao final.\n"
            f"Retorne APENAS JSON com campo 'playwright_script' (código completo) e 'requirements'."
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SCRAPER_SYSTEM_PROMPT,
            max_tokens=5000,
        )
        result.setdefault("strategy", "playwright")
        return result

    def save_spider(self, result: dict, output_dir: str, spider_name: str) -> list[str]:
        """
        Write generated spider/script files to disk.

        Parameters
        ----------
        result:
            Output from ``generate()``.
        output_dir:
            Directory where files will be saved.
        spider_name:
            Base name for the files (without extension).

        Returns
        -------
        list[str]
            Paths of the files that were written.
        """
        import os

        os.makedirs(output_dir, exist_ok=True)
        written: list[str] = []

        if result.get("scrapy_spider"):
            path = os.path.join(output_dir, f"{spider_name}.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(result["scrapy_spider"])
            written.append(path)
            log.info("scraper_saved", path=path, type="scrapy")

        if result.get("playwright_script"):
            path = os.path.join(output_dir, f"{spider_name}_playwright.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(result["playwright_script"])
            written.append(path)
            log.info("scraper_saved", path=path, type="playwright")

        return written
