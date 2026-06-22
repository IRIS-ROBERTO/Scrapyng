"""
Semantic HTML page analyzer.

Uses NVIDIA NIM to understand the structure of a web page and identify
all extractable fields, CSS selectors, XPath expressions, and the
best scraping strategy.
"""

from __future__ import annotations

import structlog

from .nvidia_client import NvidiaClient
from .prompts.page_analysis import PAGE_ANALYSIS_SYSTEM_PROMPT, build_page_analysis_prompt

log = structlog.get_logger(__name__)


class PageAnalyzer:
    """
    Analyzes HTML pages semantically to produce a structured extraction plan.

    Example
    -------
    ::

        analyzer = PageAnalyzer(nvidia_client)
        result = await analyzer.analyze(url="https://example.com", html=raw_html)
        # result["page_type"] => "cards"
        # result["extractable_fields"] => [{name, css_selector, xpath, ...}, ...]
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def analyze(self, url: str, html: str) -> dict:
        """
        Perform a semantic analysis of the page.

        Parameters
        ----------
        url:
            The page URL (used as context for relative links, etc.).
        html:
            Raw HTML content of the page.

        Returns
        -------
        dict
            Structured analysis containing:
            - ``page_type``: table | cards | list | article | form | mixed | unknown
            - ``requires_javascript``: bool
            - ``recommended_strategy``: scrapy | playwright | scrapy+playwright
            - ``pagination``: detection info
            - ``extractable_fields``: list of field descriptors
            - ``container_selector``: CSS for the parent container
            - ``item_selector``: CSS for each repeating item
            - ``notes``: any caveats
        """
        log.info("page_analyzer_start", url=url, html_len=len(html))

        user_message = build_page_analysis_prompt(url=url, html=html)

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=PAGE_ANALYSIS_SYSTEM_PROMPT,
            max_tokens=3000,
        )

        log.info(
            "page_analyzer_done",
            url=url,
            page_type=result.get("page_type"),
            fields_found=len(result.get("extractable_fields", [])),
            strategy=result.get("recommended_strategy"),
        )
        return result

    async def quick_check(self, url: str, html: str) -> dict:
        """
        Lightweight version — only detects page type and whether JS is required.
        Useful for routing decisions before full analysis.

        Returns
        -------
        dict
            ``{"page_type": str, "requires_javascript": bool, "recommended_strategy": str}``
        """
        prompt = (
            f"Responda APENAS com JSON: "
            f'{{ "page_type": "...", "requires_javascript": true/false, '
            f'"recommended_strategy": "scrapy|playwright|scrapy+playwright" }}\n\n'
            f"URL: {url}\n\n"
            f"HTML (primeiros 3000 chars):\n{html[:3000]}"
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=PAGE_ANALYSIS_SYSTEM_PROMPT,
            max_tokens=200,
        )
        return {
            "page_type": result.get("page_type", "unknown"),
            "requires_javascript": result.get("requires_javascript", False),
            "recommended_strategy": result.get("recommended_strategy", "scrapy"),
        }
