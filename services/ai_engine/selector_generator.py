"""
CSS/XPath selector generator.

Given an HTML page and a list of desired fields, this module uses NVIDIA NIM
to generate robust, resilient selectors for each field.
"""

from __future__ import annotations

import structlog

from .nvidia_client import NvidiaClient
from .prompts.selector_generation import SELECTOR_SYSTEM_PROMPT, build_selector_prompt

log = structlog.get_logger(__name__)


class SelectorGenerator:
    """
    Generates CSS and XPath selectors for specific fields on a page.

    Example
    -------
    ::

        gen = SelectorGenerator(nvidia_client)
        result = await gen.generate(
            url="https://shop.example.com/products",
            html=raw_html,
            fields=["product_name", "price", "image_url", "rating"]
        )
        for sel in result["selectors"]:
            print(sel["field_name"], sel["css"], sel["xpath"])
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def generate(
        self,
        url: str,
        html: str,
        fields: list[str],
    ) -> dict:
        """
        Generate selectors for the requested fields.

        Parameters
        ----------
        url:
            Page URL for context.
        html:
            Raw HTML of the page.
        fields:
            Human-readable field names to extract (e.g. ["price", "title"]).

        Returns
        -------
        dict
            ``{"selectors": [...], "notes": "..."}``
            Each selector entry has: field_name, css, xpath, attribute,
            post_processing, confidence, fallback_css, fallback_xpath.
        """
        log.info("selector_generator_start", url=url, fields=fields)

        user_message = build_selector_prompt(url=url, html=html, fields=fields)

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SELECTOR_SYSTEM_PROMPT,
            max_tokens=2500,
        )

        selectors = result.get("selectors", [])
        log.info(
            "selector_generator_done",
            url=url,
            selectors_generated=len(selectors),
        )
        return result

    async def generate_from_analysis(
        self,
        url: str,
        html: str,
        page_analysis: dict,
    ) -> dict:
        """
        Generate selectors using the output of PageAnalyzer as context.

        This is more accurate than calling ``generate()`` directly because
        the AI already has the page structure in its context.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML.
        page_analysis:
            Dict returned by ``PageAnalyzer.analyze()``.

        Returns
        -------
        dict
            Same structure as ``generate()``.
        """
        import json

        fields = [
            f["name"]
            for f in page_analysis.get("extractable_fields", [])
        ]
        if not fields:
            log.warning("selector_generator_no_fields", url=url)
            return {"selectors": [], "notes": "No extractable fields found in page analysis."}

        analysis_ctx = json.dumps(
            {
                "page_type": page_analysis.get("page_type"),
                "container_selector": page_analysis.get("container_selector"),
                "item_selector": page_analysis.get("item_selector"),
                "extractable_fields": page_analysis.get("extractable_fields", []),
            },
            ensure_ascii=False,
        )

        user_message = (
            f"Gere seletores CSS e XPath para os campos identificados nesta página.\n\n"
            f"URL: {url}\n\n"
            f"Análise prévia da página:\n{analysis_ctx}\n\n"
            f"HTML:\n```html\n{html[:8000]}\n```\n\n"
            f"Use a análise prévia como contexto extra. Retorne APENAS JSON válido."
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SELECTOR_SYSTEM_PROMPT,
            max_tokens=3000,
        )

        log.info(
            "selector_generator_from_analysis_done",
            url=url,
            selectors=len(result.get("selectors", [])),
        )
        return result

    def to_scrapy_dict(self, selectors_result: dict) -> dict[str, str]:
        """
        Convert selector result to a flat ``{field: css_selector}`` dict
        ready for use in a Scrapy ItemLoader.

        Parameters
        ----------
        selectors_result:
            Output from ``generate()`` or ``generate_from_analysis()``.

        Returns
        -------
        dict
            ``{"field_name": "css_selector", ...}``
        """
        out: dict[str, str] = {}
        for sel in selectors_result.get("selectors", []):
            name = sel.get("field_name", "")
            css = sel.get("css", "")
            if name and css:
                out[name] = css
        return out
