"""
Scraper Engine — motor de scraping da WebScrapy AI Platform.

Exporta as classes principais para uso externo.
"""

from .scrapy_runner import ScrapyRunner, DynamicSpider
from .playwright_runner import PlaywrightRunner
from .selector_tester import SelectorTester
from .html_table_extractor import HTMLTableExtractor
from .job_executor import JobExecutor
from .result_normalizer import ResultNormalizer
from .version_manager import VersionManager

__all__ = [
    "ScrapyRunner",
    "DynamicSpider",
    "PlaywrightRunner",
    "SelectorTester",
    "HTMLTableExtractor",
    "JobExecutor",
    "ResultNormalizer",
    "VersionManager",
]
