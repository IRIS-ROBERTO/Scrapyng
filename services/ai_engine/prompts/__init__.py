"""
Prompt templates for WebScrapy AI Engine.
Each module contains system and user prompts for a specific task.
"""

from .page_analysis import PAGE_ANALYSIS_SYSTEM_PROMPT, build_page_analysis_prompt
from .selector_generation import SELECTOR_SYSTEM_PROMPT, build_selector_prompt
from .scraper_generation import SCRAPER_SYSTEM_PROMPT, build_scraper_prompt
from .scraper_repair import REPAIR_SYSTEM_PROMPT, build_repair_prompt
from .data_structuring import STRUCTURING_SYSTEM_PROMPT, build_structuring_prompt
from .search_types import (
    FLIGHTS_SYSTEM_PROMPT,
    NEWS_SYSTEM_PROMPT,
    LEADS_SYSTEM_PROMPT,
    JOBS_SYSTEM_PROMPT,
    build_flights_prompt,
    build_news_prompt,
    build_leads_prompt,
    build_jobs_prompt,
)

__all__ = [
    "PAGE_ANALYSIS_SYSTEM_PROMPT",
    "build_page_analysis_prompt",
    "SELECTOR_SYSTEM_PROMPT",
    "build_selector_prompt",
    "SCRAPER_SYSTEM_PROMPT",
    "build_scraper_prompt",
    "REPAIR_SYSTEM_PROMPT",
    "build_repair_prompt",
    "STRUCTURING_SYSTEM_PROMPT",
    "build_structuring_prompt",
    "FLIGHTS_SYSTEM_PROMPT",
    "NEWS_SYSTEM_PROMPT",
    "LEADS_SYSTEM_PROMPT",
    "JOBS_SYSTEM_PROMPT",
    "build_flights_prompt",
    "build_news_prompt",
    "build_leads_prompt",
    "build_jobs_prompt",
]
