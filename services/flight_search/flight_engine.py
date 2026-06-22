"""
Motor de busca de passagens aéreas.

Orquestra:
- Amadeus API (primário, se configurado)
- Playwright/Google Flights (fallback)
- Busca em múltiplos aeroportos dos EUA
- Flexibilidade de +/- N dias na data
- Resultado final ranqueado por preço (menor para maior)
"""

from __future__ import annotations

import asyncio
import unicodedata
from datetime import date, timedelta
from typing import Any

from .airport_codes import BRAZIL_AIRPORTS, city_to_iata, get_us_airports_for_search
from services.logger import get_logger

log = get_logger(__name__)

MAX_US_AIRPORTS = 15
MAX_CONCURRENCY = 6


class FlightSearchEngine:
    """
    Motor principal de busca de passagens.

    Uso:
        engine = FlightSearchEngine()
        results = await engine.search(
            origin_city="Sao Paulo",
            destination_country="EUA",
            destination_city="",
            departure_date="2026-11-13",
            return_date="2026-06-21",
            passengers=1,
            date_flexibility_days=3,
        )
    """

    def __init__(self, amadeus_key: str = "", amadeus_secret: str = "") -> None:
        self.amadeus_client: Any = None
        self.scraper: Any = None

        if amadeus_key and amadeus_secret:
            try:
                from .amadeus_client import AmadeusClient
                self.amadeus_client = AmadeusClient(amadeus_key, amadeus_secret)
                log.info("amadeus_client_ready")
            except Exception as e:
                log.warning("amadeus_init_failed", error=str(e))

    async def search(
        self,
        origin_city: str,
        destination_country: str,
        destination_city: str = "",
        departure_date: str = "",
        return_date: str | None = None,
        passengers: int = 1,
        date_flexibility_days: int = 3,
        currency: str = "BRL",
    ) -> list[dict[str, Any]]:
        """
        Busca passagens com flexibilidade de datas e múltiplos destinos.
        Retorna lista ordenada por preço (menor primeiro).
        """
        origin_iata = self._resolve_origin(origin_city)
        if not origin_iata:
            log.error("origin_iata_not_found", city=origin_city)
            return []

        dest_airports = self._resolve_destinations(destination_country, destination_city)
        if not dest_airports:
            log.error("no_dest_airports", country=destination_country)
            return []

        dep_dates = self._generate_date_range(departure_date, date_flexibility_days)
        if not dep_dates:
            dep_dates = [departure_date] if departure_date else []

        log.info(
            "flight_search_start",
            origin=origin_iata,
            destinations=len(dest_airports),
            dep_dates=len(dep_dates),
        )

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        tasks = []
        for dest in dest_airports[:MAX_US_AIRPORTS]:
            for dep_date in dep_dates:
                tasks.append(
                    self._search_one(
                        sem,
                        origin_iata, origin_city,
                        dest["iata"], dest.get("city", dest["iata"]),
                        dep_date, return_date,
                        passengers, currency,
                        departure_date_original=departure_date,
                    )
                )

        batches = await asyncio.gather(*tasks)

        all_results: list[dict] = []
        for batch in batches:
            if batch:
                all_results.extend(batch)

        unique = self._deduplicate(all_results)
        unique.sort(key=lambda x: float(x.get("preco", 999999) or 999999))

        log.info("flight_search_done", total=len(unique))
        return unique

    async def _search_one(
        self,
        sem: asyncio.Semaphore,
        origin_iata: str,
        origin_city: str,
        dest_iata: str,
        dest_city: str,
        dep_date: str,
        ret_date: str | None,
        passengers: int,
        currency: str,
        departure_date_original: str,
    ) -> list[dict]:
        async with sem:
            results: list[dict] = []

            if self.amadeus_client:
                try:
                    loop = asyncio.get_event_loop()
                    raw = await loop.run_in_executor(
                        None,
                        lambda: self.amadeus_client.search_flight_offers(
                            origin_iata, dest_iata, dep_date, ret_date, passengers, currency
                        ),
                    )
                    results = raw or []
                except Exception as e:
                    log.debug("amadeus_one_failed", error=str(e))

            if not results:
                try:
                    if self.scraper is None:
                        from .playwright_scraper import FlightPlaywrightScraper
                        self.scraper = FlightPlaywrightScraper()
                    results = await self.scraper.search(origin_iata, dest_iata, dep_date, ret_date, passengers)
                except Exception as e:
                    log.debug("playwright_one_failed", error=str(e))

            enriched: list[dict] = []
            for r in results:
                try:
                    dep_date_obj = date.fromisoformat(dep_date)
                    orig_dep = date.fromisoformat(departure_date_original) if departure_date_original else dep_date_obj
                    diff = (dep_date_obj - orig_dep).days
                    enriched.append({
                        **r,
                        "origem_iata": origin_iata,
                        "origem_cidade": origin_city,
                        "destino_iata": dest_iata,
                        "destino_cidade": dest_city,
                        "data_ida_real": dep_date,
                        "data_volta_real": ret_date,
                        "diferenca_dias": diff,
                        "passageiros": passengers,
                    })
                except Exception:
                    enriched.append(r)
            return enriched

    @staticmethod
    def _resolve_origin(city: str) -> str:
        if len(city) == 3 and city.upper() == city:
            return city.upper()
        key = city.strip().lower().split(",")[0].strip()
        key_ascii = _normalize(key)
        code = BRAZIL_AIRPORTS.get(key) or BRAZIL_AIRPORTS.get(key_ascii)
        if code:
            return code
        for k, v in BRAZIL_AIRPORTS.items():
            if k in key or key in k or k in key_ascii or key_ascii in k:
                return v
        return "GRU"

    @staticmethod
    def _resolve_destinations(country: str, specific_city: str) -> list[dict]:
        is_usa = any(w in country.lower() for w in ["eua", "united states", "usa", "estados unidos"])
        if is_usa:
            return get_us_airports_for_search(specific_city)
        iata = city_to_iata(specific_city or country, country)
        if iata:
            return [{"iata": iata, "city": specific_city or country, "country": country}]
        return []

    @staticmethod
    def _generate_date_range(base_date: str | None, flexibility: int) -> list[str]:
        if not base_date:
            return []
        try:
            d = date.fromisoformat(base_date)
        except ValueError:
            return [base_date]
        today = date.today()
        return [
            (d + timedelta(days=delta)).isoformat()
            for delta in range(-flexibility, flexibility + 1)
            if (d + timedelta(days=delta)) >= today
        ]

    @staticmethod
    def _deduplicate(results: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for r in results:
            key = (
                f"{r.get('origem_iata','')}"
                f"-{r.get('destino_iata','')}"
                f"-{r.get('data_ida_real','')}"
                f"-{r.get('preco','')}"
                f"-{r.get('companhia','')}"
            )
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def create_engine_from_env() -> FlightSearchEngine:
    import os
    key = os.environ.get("AMADEUS_API_KEY", "")
    secret = os.environ.get("AMADEUS_API_SECRET", "")
    return FlightSearchEngine(amadeus_key=key, amadeus_secret=secret)
