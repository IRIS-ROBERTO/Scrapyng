"""
Amadeus Flight Offers Search API client.
API gratuita em https://developers.amadeus.com/ (500 req/mês no plano free).

Autenticação: OAuth2 Client Credentials (AMADEUS_API_KEY + AMADEUS_API_SECRET).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx
from services.logger import get_logger

log = get_logger(__name__)


class AmadeusClient:
    """
    Wrapper para a API de ofertas de voo da Amadeus.

    Ambiente de teste (default) usa dados reais mas em sandbox:
    https://test.api.amadeus.com

    Troque para https://api.amadeus.com em produção (plano pago).
    """

    BASE_URL = "https://test.api.amadeus.com"
    TOKEN_URL = f"{BASE_URL}/v1/security/oauth2/token"
    OFFERS_URL = f"{BASE_URL}/v2/shopping/flight-offers"
    DESTINATIONS_URL = f"{BASE_URL}/v1/shopping/flight-destinations"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self._token: str | None = None
        self._token_expires: datetime = datetime.min

    def _ensure_token(self) -> None:
        """Obtém/renova token OAuth2."""
        if self._token and datetime.utcnow() < self._token_expires:
            return

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires = datetime.utcnow() + timedelta(
                seconds=data.get("expires_in", 1799) - 30
            )
        log.info("amadeus_token_renewed")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        currency: str = "BRL",
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Busca ofertas de voo.

        Retorna lista de dicts padronizados:
        {
          companhia, numero_voo, origem, destino,
          saida, chegada, duracao, escalas,
          preco, moeda, link_compra, fonte
        }
        """
        self._ensure_token()
        params: dict[str, Any] = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": currency,
            "max": min(max_results, 50),
        }
        if return_date:
            params["returnDate"] = return_date

        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(self.OFFERS_URL, params=params, headers=self._headers())
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning("amadeus_error", status=e.response.status_code, origin=origin, dest=destination)
            return []
        except Exception as e:
            log.warning("amadeus_request_failed", error=str(e))
            return []

        results = []
        for offer in data.get("data", []):
            try:
                price = float(offer["price"]["grandTotal"])
                currency_code = offer["price"]["currency"]

                # Primeiro itinerário (ida)
                itinerary = offer["itineraries"][0]
                segments = itinerary["segments"]
                first_seg = segments[0]
                last_seg = segments[-1]

                airline_code = first_seg["carrierCode"]
                carriers = data.get("dictionaries", {}).get("carriers", {})
                airline_name = carriers.get(airline_code, airline_code)

                departure_dt = first_seg["departure"]["at"]
                arrival_dt = last_seg["arrival"]["at"]
                duration_str = itinerary["duration"]  # e.g. "PT10H30M"
                stops = len(segments) - 1

                results.append({
                    "companhia": airline_name,
                    "codigo_companhia": airline_code,
                    "numero_voo": f"{airline_code}{first_seg['number']}",
                    "origem": origin,
                    "destino": destination,
                    "saida": departure_dt,
                    "chegada": arrival_dt,
                    "duracao": _format_duration(duration_str),
                    "escalas": stops,
                    "preco": price,
                    "moeda": currency_code,
                    "link_compra": f"https://www.google.com/flights#flt={origin}.{destination}.{departure_date}",
                    "fonte": "Amadeus",
                })
            except (KeyError, ValueError, TypeError) as e:
                log.debug("amadeus_parse_error", error=str(e))
                continue

        log.info("amadeus_results", origin=origin, dest=destination, date=departure_date, count=len(results))
        return results

    def get_cheapest_destinations(
        self,
        origin: str,
        departure_date: str,
        currency: str = "BRL",
        country_code: str = "US",
    ) -> list[dict[str, Any]]:
        """
        Busca os destinos mais baratos a partir de uma origem.
        Ótimo para 'qualquer cidade dos EUA'.
        """
        self._ensure_token()
        params = {
            "origin": origin,
            "departureDate": departure_date,
            "currency": currency,
            "viewBy": "DESTINATION",
        }

        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(self.DESTINATIONS_URL, params=params, headers=self._headers())
                if resp.status_code in (404, 400):
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("amadeus_destinations_failed", error=str(e))
            return []

        results = []
        for dest in data.get("data", []):
            try:
                dest_code = dest["destination"]
                price = float(dest["price"]["total"])
                dep_date = dest["departureDate"]
                ret_date = dest.get("returnDate")
                results.append({
                    "destino": dest_code,
                    "preco": price,
                    "moeda": currency,
                    "saida": dep_date,
                    "volta": ret_date,
                    "fonte": "Amadeus Inspiration",
                })
            except (KeyError, ValueError):
                continue

        return sorted(results, key=lambda x: x["preco"])


def _format_duration(iso_duration: str) -> str:
    """Converte 'PT10H30M' → '10h 30min'."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_duration)
    if not match:
        return iso_duration
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}min")
    return " ".join(parts) or "0min"
