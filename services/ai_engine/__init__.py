"""
WebScrapy AI Engine
===================

Central AI module powered by NVIDIA NIM with automatic model fallback.

Provides specialized AI agents for:
- Page structure analysis
- CSS/XPath selector generation
- Scrapy spider and Playwright script generation
- Broken scraper auto-repair
- Raw data structuring and normalization
- Data quality validation
- Executive insight generation
- Specialized search extraction (flights, news, leads, jobs)

Quick start::

    import os
    from services.ai_engine import AIEngine

    engine = AIEngine(nvidia_api_key=os.environ["NVIDIA_API_KEY"])

    # Analyze a page
    analysis = await engine.page_analyzer.analyze(url, html)

    # Generate a spider
    spider = await engine.scraper_generator.generate(url, analysis, fields)

    # Extract flights from a travel page
    flights = await engine.search_intelligence.analyze_flight_search(url, html, params)
"""

from __future__ import annotations

import os

from .nvidia_client import NvidiaClient, NvidiaClientError, NVIDIA_MODELS_FALLBACK
from .page_analyzer import PageAnalyzer
from .selector_generator import SelectorGenerator
from .scraper_generator import ScraperGenerator
from .scraper_repair_agent import ScraperRepairAgent
from .data_structuring_agent import DataStructuringAgent
from .data_validation_agent import DataValidationAgent
from .insight_agent import InsightAgent
from .search_intelligence import SearchIntelligence

__all__ = [
    "AIEngine",
    "NvidiaClient",
    "NvidiaClientError",
    "NVIDIA_MODELS_FALLBACK",
    "PageAnalyzer",
    "SelectorGenerator",
    "ScraperGenerator",
    "ScraperRepairAgent",
    "DataStructuringAgent",
    "DataValidationAgent",
    "InsightAgent",
    "SearchIntelligence",
]

__version__ = "1.0.0"


class AIEngine:
    """
    Facade that wires all AI agents together around a shared NvidiaClient.

    All agents share the same client instance (and therefore the same
    API key and fallback model chain).

    Parameters
    ----------
    nvidia_api_key:
        NVIDIA NIM API key. If not provided, read from ``NVIDIA_API_KEY``
        environment variable.
    base_url:
        NVIDIA NIM base URL. Defaults to the public endpoint.
    models:
        Custom model fallback chain. Defaults to ``NVIDIA_MODELS_FALLBACK``.

    Example
    -------
    ::

        engine = AIEngine()  # reads NVIDIA_API_KEY from env

        # Analyze page structure
        analysis = await engine.page_analyzer.analyze(url, html)

        # Generate scraper
        spider_result = await engine.scraper_generator.generate(
            url, analysis, target_fields=["title", "price"]
        )

        # Search intelligence
        flights = await engine.search.analyze_flight_search(url, html, {})
        news    = await engine.search.analyze_news_search(url, html, {"query": "AI"})
        jobs    = await engine.search.analyze_jobs_search(url, html, {})
        leads   = await engine.search.analyze_leads_search(url, html, {})
    """

    def __init__(
        self,
        nvidia_api_key: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        models: list[str] | None = None,
    ) -> None:
        api_key = nvidia_api_key or os.environ["NVIDIA_API_KEY"]

        self._client = NvidiaClient(
            api_key=api_key,
            base_url=base_url,
            models=models,
        )

        # Instantiate all agents
        self.page_analyzer = PageAnalyzer(self._client)
        self.selector_generator = SelectorGenerator(self._client)
        self.scraper_generator = ScraperGenerator(self._client)
        self.scraper_repair = ScraperRepairAgent(self._client)
        self.data_structuring = DataStructuringAgent(self._client)
        self.data_validation = DataValidationAgent(self._client)
        self.insight = InsightAgent(self._client)
        self.search = SearchIntelligence(self._client)

        # Alias for ergonomics
        self.search_intelligence = self.search

    @property
    def client(self) -> NvidiaClient:
        """Access the underlying NvidiaClient directly if needed."""
        return self._client

    async def full_pipeline(
        self,
        url: str,
        html: str,
        target_fields: list[str] | None = None,
        spider_name: str = "auto_spider",
        search_params: dict | None = None,
    ) -> dict:
        """
        Run the full AI pipeline on a page:
        Analyze → Generate Selectors → Generate Scraper → Detect Search Type.

        Parameters
        ----------
        url:
            Target page URL.
        html:
            Raw HTML content.
        target_fields:
            Fields to extract. If None, uses all fields detected by PageAnalyzer.
        spider_name:
            Name for the generated spider.
        search_params:
            Optional params forwarded to SearchIntelligence.

        Returns
        -------
        dict
            Combined result with keys:
            analysis, selectors, scraper, search_type.
        """
        # Step 1: Analyze page structure
        analysis = await self.page_analyzer.analyze(url=url, html=html)

        # Step 2: Determine target fields
        fields = target_fields or [
            f["name"] for f in analysis.get("extractable_fields", [])
        ]

        # Step 3: Generate selectors
        selectors = await self.selector_generator.generate_from_analysis(
            url=url, html=html, page_analysis=analysis
        )

        # Step 4: Generate scraper code
        scraper = await self.scraper_generator.generate(
            url=url,
            page_analysis=analysis,
            target_fields=fields,
            spider_name=spider_name,
        )

        # Step 5: Detect search type (fast, heuristic)
        search_type = await self.search.detect_search_type(url=url)

        return {
            "url": url,
            "analysis": analysis,
            "selectors": selectors,
            "scraper": scraper,
            "search_type": search_type,
            "target_fields": fields,
        }
