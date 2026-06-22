"""
Scraper auto-repair agent.

When a scraper breaks (DOM change, selector mismatch, schema change, etc.)
this agent compares the old vs. new HTML, diagnoses the root cause, and
generates a corrected version of the scraper code.
"""

from __future__ import annotations

import difflib
import structlog

from .nvidia_client import NvidiaClient
from .prompts.scraper_repair import REPAIR_SYSTEM_PROMPT, build_repair_prompt

log = structlog.get_logger(__name__)


class ScraperRepairAgent:
    """
    Automatically repairs broken scraper code by analysing DOM diffs.

    Example
    -------
    ::

        agent = ScraperRepairAgent(nvidia_client)
        result = await agent.repair(
            original_code=old_spider_code,
            old_html=html_when_working,
            new_html=html_now_broken,
            error_message=traceback_str,
        )
        print(result["diagnosis"])
        print(result["repaired_code"])
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def repair(
        self,
        original_code: str,
        old_html: str,
        new_html: str,
        error_message: str,
    ) -> dict:
        """
        Diagnose and repair a broken scraper.

        Parameters
        ----------
        original_code:
            The Python spider/script that is currently failing.
        old_html:
            HTML snapshot from when the scraper was working.
        new_html:
            Current HTML that is causing the scraper to fail.
        error_message:
            Exception message or traceback from the failed run.

        Returns
        -------
        dict
            - ``diagnosis``: human-readable explanation of the breakage
            - ``root_cause``: category of the change
            - ``changes_detected``: list of per-field selector changes
            - ``repaired_code``: full corrected Python code
            - ``confidence``: high | medium | low
            - ``additional_recommendations``: optional further advice
        """
        log.info(
            "repair_agent_start",
            original_code_lines=original_code.count("\n"),
            old_html_len=len(old_html),
            new_html_len=len(new_html),
        )

        # Compute a structural diff summary to include in the prompt
        dom_diff_summary = self._structural_diff(old_html, new_html)

        # Enrich the error message with the diff summary
        enriched_error = f"{error_message}\n\nDOM DIFF SUMMARY:\n{dom_diff_summary}"

        user_message = build_repair_prompt(
            original_code=original_code,
            old_html=old_html,
            new_html=new_html,
            error_message=enriched_error,
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=REPAIR_SYSTEM_PROMPT,
            max_tokens=5000,
        )

        log.info(
            "repair_agent_done",
            root_cause=result.get("root_cause"),
            changes=len(result.get("changes_detected", [])),
            confidence=result.get("confidence"),
        )
        return result

    async def quick_diagnose(
        self,
        error_message: str,
        code_snippet: str,
    ) -> dict:
        """
        Fast diagnosis when old HTML is not available — works from error alone.

        Parameters
        ----------
        error_message:
            Exception / traceback text.
        code_snippet:
            The relevant portion of the spider code.

        Returns
        -------
        dict
            ``{"diagnosis": str, "likely_cause": str, "suggested_fix": str}``
        """
        prompt = (
            f"Um scraper Scrapy/Playwright falhou. Diagnostique rapidamente.\n\n"
            f"ERRO:\n{error_message}\n\n"
            f"TRECHO DE CÓDIGO:\n```python\n{code_snippet[:3000]}\n```\n\n"
            f"Retorne JSON: "
            f'{{ "diagnosis": "...", "likely_cause": "...", "suggested_fix": "..." }}'
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=REPAIR_SYSTEM_PROMPT,
            max_tokens=800,
        )
        log.info("repair_agent_quick_diagnose_done", cause=result.get("likely_cause"))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _structural_diff(old_html: str, new_html: str, context_lines: int = 3) -> str:
        """
        Produce a compact unified diff between old and new HTML.

        The diff is truncated to avoid overloading the prompt.
        """
        old_lines = old_html.splitlines(keepends=True)
        new_lines = new_html.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                old_lines[:300],   # cap to first 300 lines each
                new_lines[:300],
                fromfile="old_html",
                tofile="new_html",
                n=context_lines,
            )
        )

        # Limit diff output to 150 lines to stay within token budget
        diff_text = "".join(diff[:150])
        if len(diff) > 150:
            diff_text += f"\n... ({len(diff) - 150} more lines omitted)"

        return diff_text if diff_text else "(No structural differences detected in sampled HTML)"
