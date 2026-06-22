"""
Search intelligence — specialized AI for specific search types.

Each search type (flights, news, leads, jobs) has a dedicated method with
a tailored system prompt and extraction strategy optimized for that domain.
"""

from __future__ import annotations

import re
import structlog
from urllib.parse import urlparse

from .nvidia_client import NvidiaClient
from .prompts.search_types import (
    FLIGHTS_SYSTEM_PROMPT,
    NEWS_SYSTEM_PROMPT,
    LEADS_SYSTEM_PROMPT,
    JOBS_SYSTEM_PROMPT,
    build_flights_prompt,
    build_news_prompt,
    build_leads_prompt,
    build_jobs_prompt,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Search type detection heuristics
# ---------------------------------------------------------------------------
_FLIGHT_DOMAINS = frozenset({
    "kayak", "google.com/flights", "decolar", "viajanet", "maxmilhas",
    "latam", "gol", "azul", "avianca", "skyscanner", "momondo",
    "booking.com/flights", "expedia", "cheapflights",
})

_NEWS_DOMAINS = frozenset({
    "g1.globo", "uol.com.br", "folha.uol", "estadao.com.br", "reuters.com",
    "bbc.com", "cnn.com", "elpaisbrasil", "exame.com", "infomoney.com.br",
    "techcrunch.com", "theverge.com", "wired.com", "agenciabrasil",
})

_JOBS_DOMAINS = frozenset({
    "linkedin.com/jobs", "indeed.com", "glassdoor.com", "catho.com.br",
    "infojobs.com.br", "gupy.io", "vagas.com.br", "99jobs.com",
    "remote.co", "weworkremotely.com", "stackoverflow.com/jobs",
})

_LEADS_DOMAINS = frozenset({
    "linkedin.com/company", "linkedin.com/in/", "apollo.io", "hunter.io",
    "crunchbase.com", "angellist.com", "clutch.co", "g2.com",
    "capterra.com", "zoominfo.com",
})

_FLIGHT_URL_PATTERNS = re.compile(
    r"(passag|flight|voo|bilhet|airfare|ticket)", re.IGNORECASE
)
_NEWS_URL_PATTERNS = re.compile(
    r"(notici|notic|news|article|artigo|report|jornal)", re.IGNORECASE
)
_JOBS_URL_PATTERNS = re.compile(
    r"(vaga|emprego|job|career|carreira|work|trabalh)", re.IGNORECASE
)
_LEADS_URL_PATTERNS = re.compile(
    r"(lead|prospect|contact|empresa|company|diret)", re.IGNORECASE
)

# System prompt for type detection
_DETECT_SYSTEM_PROMPT = """Você é um classificador de intenção de busca web.
Dada uma URL e contexto, determine o tipo de busca.
Retorne APENAS JSON: {"type": "flights|news|leads|jobs|generic", "confidence": "high|medium|low", "reasoning": "string"}"""


class SearchIntelligence:
    """
    AI specialized in specific search types with domain-optimized extraction.

    Automatically detects the search type from URL heuristics and routes
    to the appropriate specialized extractor.

    Example
    -------
    ::

        si = SearchIntelligence(nvidia_client)

        # Auto-detect and extract
        result = await si.extract(url=url, html=html, params={})

        # Or use specialized methods directly
        flights = await si.analyze_flight_search(url, html, {"origin": "GRU"})
        news    = await si.analyze_news_search(url, html, {"query": "AI"})
        leads   = await si.analyze_leads_search(url, html, {"industry": "SaaS"})
        jobs    = await si.analyze_jobs_search(url, html, {"user_skills": ["Python"]})
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Auto-routing entry point
    # ------------------------------------------------------------------

    async def extract(
        self,
        url: str,
        html: str,
        params: dict,
        search_type: str | None = None,
    ) -> dict:
        """
        Extract data from a page using the appropriate specialized method.

        If ``search_type`` is not provided, it is detected automatically.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML of the page.
        params:
            Search parameters (origin, destination, query, skills, etc.).
        search_type:
            Optional override: 'flights' | 'news' | 'leads' | 'jobs' | 'generic'.

        Returns
        -------
        dict
            Extraction result from the appropriate specialized method.
        """
        if search_type is None:
            search_type = await self.detect_search_type(url=url, context=params.get("query", ""))

        log.info("search_intelligence_route", url=url, search_type=search_type)

        dispatch = {
            "flights": self.analyze_flight_search,
            "news": self.analyze_news_search,
            "leads": self.analyze_leads_search,
            "jobs": self.analyze_jobs_search,
        }

        handler = dispatch.get(search_type)
        if handler:
            result = await handler(url=url, html=html, params=params)
        else:
            result = await self._generic_extraction(url=url, html=html, params=params)

        result["_search_type"] = search_type
        return result

    # ------------------------------------------------------------------
    # Specialized extractors
    # ------------------------------------------------------------------

    async def analyze_flight_search(self, url: str, html: str, params: dict) -> dict:
        """
        Extract flight data from airline/travel booking pages.

        Detects: prices, schedules, airlines, stops, baggage, booking URLs.
        Computes: cheapest option, best value option, price alerts.

        Supported sites: Kayak, Google Flights, Decolar, ViajaNet, MaxMilhas,
        Latam, Gol, Azul, Avianca, Skyscanner.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML.
        params:
            Dict with optional keys: origin, destination, departure_date,
            return_date, passengers, cabin_class.

        Returns
        -------
        dict
            Flights list with cheapest_option, best_value_option, currency,
            search_params, price_alerts.
        """
        log.info("search_intelligence_flights", url=url)
        user_message = build_flights_prompt(url=url, html=html, params=params)
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=FLIGHTS_SYSTEM_PROMPT,
            max_tokens=5000,
        )
        result.setdefault("source_url", url)
        log.info(
            "search_intelligence_flights_done",
            url=url,
            flights_found=len(result.get("flights", [])),
        )
        return result

    async def analyze_news_search(self, url: str, html: str, params: dict) -> dict:
        """
        Extract news articles from news portal pages.

        Detects: title, subtitle, summary, full content, image URL, author,
        publication date, tags, relevance score.

        Supported sites: G1, UOL, Folha, Estadão, Reuters, BBC, CNN,
        El País Brasil, Exame, InfoMoney, TechCrunch, The Verge.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML.
        params:
            Dict with optional key: ``query`` (search term for relevance scoring).

        Returns
        -------
        dict
            Articles list with total_found, most_relevant index.
        """
        log.info("search_intelligence_news", url=url, query=params.get("query"))
        user_message = build_news_prompt(url=url, html=html, params=params)
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=NEWS_SYSTEM_PROMPT,
            max_tokens=5000,
        )
        result.setdefault("source_url", url)
        log.info(
            "search_intelligence_news_done",
            url=url,
            articles_found=len(result.get("articles", [])),
        )
        return result

    async def analyze_leads_search(self, url: str, html: str, params: dict) -> dict:
        """
        Extract B2B leads (companies and contacts) from prospecting pages.

        Detects: company name, website, industry, size, contact name, title,
        email, phone, LinkedIn, country, technologies, quality score.

        Supported sites: LinkedIn, Apollo.io, Hunter.io, ZoomInfo, Crunchbase,
        AngelList, Clutch, G2, Capterra, sectoral directories.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML.
        params:
            Dict with optional keys: target_industry, target_country,
            company_size, keywords.

        Returns
        -------
        dict
            Leads list with high_quality_count and search_params.
        """
        log.info("search_intelligence_leads", url=url)
        user_message = build_leads_prompt(url=url, html=html, params=params)
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=LEADS_SYSTEM_PROMPT,
            max_tokens=5000,
        )
        result.setdefault("source_url", url)
        leads = result.get("leads", [])
        high_quality = sum(1 for l in leads if (l.get("quality_score") or 0) >= 70)
        result["high_quality_count"] = high_quality
        log.info(
            "search_intelligence_leads_done",
            url=url,
            leads_found=len(leads),
            high_quality=high_quality,
        )
        return result

    async def analyze_jobs_search(self, url: str, html: str, params: dict) -> dict:
        """
        Extract job listings from employment platforms.

        Detects: title, seniority, company, location, salary, contract type,
        remote/hybrid, requirements, skills, benefits, apply URL, match score.

        Supported sites: LinkedIn Jobs, Indeed, Glassdoor, Catho, InfoJobs,
        Gupy, Vagas.com, 99Jobs, Remote.co, We Work Remotely.

        Parameters
        ----------
        url:
            Page URL.
        html:
            Raw HTML.
        params:
            Dict with optional keys: query, location, remote_only,
            user_skills (list of skills for match scoring).

        Returns
        -------
        dict
            Jobs list with best_match_index and search_params.
        """
        log.info("search_intelligence_jobs", url=url, query=params.get("query"))
        user_message = build_jobs_prompt(url=url, html=html, params=params)
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=JOBS_SYSTEM_PROMPT,
            max_tokens=5000,
        )
        result.setdefault("source_url", url)

        # Compute best_match_index from match_score
        jobs = result.get("jobs", [])
        if jobs and "best_match_index" not in result:
            best_idx = max(
                range(len(jobs)),
                key=lambda i: jobs[i].get("match_score") or 0,
                default=None,
            )
            result["best_match_index"] = best_idx

        log.info(
            "search_intelligence_jobs_done",
            url=url,
            jobs_found=len(jobs),
            best_match=result.get("best_match_index"),
        )
        return result

    # ------------------------------------------------------------------
    # Type detection
    # ------------------------------------------------------------------

    async def detect_search_type(self, url: str, context: str = "") -> str:
        """
        Detect the search type from URL and context.

        Uses fast heuristics first; falls back to AI only when ambiguous.

        Parameters
        ----------
        url:
            The page URL to classify.
        context:
            Additional context (user query, task description, etc.).

        Returns
        -------
        str
            One of: 'flights' | 'news' | 'leads' | 'jobs' | 'generic'
        """
        # --- Fast heuristic check ---
        domain_type = self._heuristic_detect(url)
        if domain_type != "generic":
            log.info("search_type_detected_heuristic", url=url, type=domain_type)
            return domain_type

        # --- AI-based detection for ambiguous URLs ---
        log.info("search_type_ai_detection", url=url)
        prompt = (
            f"Classifique o tipo de busca desta URL.\n\n"
            f"URL: {url}\n"
            f"Contexto adicional: {context or 'nenhum'}\n\n"
            f"Retorne APENAS JSON: "
            f'{{ "type": "flights|news|leads|jobs|generic", "confidence": "high|medium|low", "reasoning": "string" }}'
        )
        try:
            result = await self._client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=_DETECT_SYSTEM_PROMPT,
                max_tokens=200,
            )
            detected = result.get("type", "generic")
            log.info(
                "search_type_detected_ai",
                url=url,
                type=detected,
                confidence=result.get("confidence"),
            )
            return detected
        except Exception as exc:
            log.warning("search_type_detection_failed", url=url, error=str(exc))
            return "generic"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _heuristic_detect(self, url: str) -> str:
        """Rule-based type detection using known domains and URL patterns."""
        try:
            parsed = urlparse(url)
            domain = (parsed.netloc + parsed.path).lower()
        except Exception:
            domain = url.lower()

        for known in _FLIGHT_DOMAINS:
            if known in domain:
                return "flights"
        for known in _NEWS_DOMAINS:
            if known in domain:
                return "news"
        for known in _JOBS_DOMAINS:
            if known in domain:
                return "jobs"
        for known in _LEADS_DOMAINS:
            if known in domain:
                return "leads"

        full_url = url.lower()
        if _FLIGHT_URL_PATTERNS.search(full_url):
            return "flights"
        if _NEWS_URL_PATTERNS.search(full_url):
            return "news"
        if _JOBS_URL_PATTERNS.search(full_url):
            return "jobs"
        if _LEADS_URL_PATTERNS.search(full_url):
            return "leads"

        return "generic"

    async def _generic_extraction(self, url: str, html: str, params: dict) -> dict:
        """Fallback generic extraction when no specialized handler matches."""
        import json

        truncated = html[:8000] if len(html) > 8000 else html
        params_str = json.dumps(params, ensure_ascii=False)

        prompt = (
            f"Extraia todos os dados relevantes desta página web.\n\n"
            f"URL: {url}\n"
            f"Parâmetros: {params_str}\n\n"
            f"HTML:\n```html\n{truncated}\n```\n\n"
            f"Retorne JSON com campo 'items' (lista de objetos extraídos) e 'total_found'."
        )

        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        result.setdefault("source_url", url)
        return result
