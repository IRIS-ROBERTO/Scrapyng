"""
Rotas de Busca Especializada — passagens aéreas (e futuramente notícias, leads, vagas).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/search", tags=["Search"])
log = logging.getLogger(__name__)

# Engine de busca (singleton lazy)
_flight_engine: Any = None


def _get_flight_engine() -> Any:
    global _flight_engine
    if _flight_engine is None:
        try:
            from services.flight_search.flight_engine import FlightSearchEngine
            _flight_engine = FlightSearchEngine(
                amadeus_key=getattr(settings, "AMADEUS_API_KEY", ""),
                amadeus_secret=getattr(settings, "AMADEUS_API_SECRET", ""),
            )
            log.info("flight_engine_initialized")
        except Exception as e:
            log.error("flight_engine_init_failed", error=str(e))
            raise
    return _flight_engine


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FlightSearchRequest(BaseModel):
    origin: str = Field(..., description="Cidade/país de origem (ex: 'São Paulo, Brasil')")
    destination: str = Field(..., description="Cidade/país de destino (ex: 'Miami, EUA')")
    departure_date: str = Field(..., description="Data de ida YYYY-MM-DD")
    return_date: str | None = Field(None, description="Data de volta YYYY-MM-DD (opcional)")
    passengers: int = Field(1, ge=1, le=9)
    date_flexibility_days: int = Field(3, ge=0, le=7, description="Dias de flexibilidade +/-")
    destination_country: str = Field("", description="País de destino (para busca 'qualquer cidade')")
    destination_city: str = Field("", description="Cidade específica (vazio = todas as cidades do país)")
    origin_city: str = Field("", description="Cidade de origem normalizada")


class FlightResult(BaseModel):
    companhia: str
    numero_voo: str
    origem_iata: str
    origem_cidade: str
    destino_iata: str
    destino_cidade: str
    saida: str
    chegada: str
    duracao: str
    escalas: int
    preco: float
    moeda: str
    data_ida_real: str
    data_volta_real: str | None
    diferenca_dias: int
    passageiros: int
    link_compra: str
    fonte: str


class FlightSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int
    cheapest_price: float | None
    cheapest_destination: str | None
    cheapest_date: str | None
    has_api_key: bool
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/flights", response_model=FlightSearchResponse)
async def search_flights(req: FlightSearchRequest) -> FlightSearchResponse:
    """
    Busca passagens aéreas com:
    - Múltiplos aeroportos dos EUA (quando destino = 'qualquer cidade')
    - Flexibilidade de +/- N dias na data solicitada
    - Resultados ranqueados por preço (menor para maior)
    """
    has_key = bool(
        getattr(settings, "AMADEUS_API_KEY", "") and
        getattr(settings, "AMADEUS_API_SECRET", "")
    )

    # Resolve parâmetros de destino
    destination_country = req.destination_country or _extract_country(req.destination)
    destination_city = req.destination_city or _extract_city(req.destination)
    origin_city = req.origin_city or req.origin

    log.info(
        "flight_search_request origin=%s dest_country=%s dest_city=%s dep=%s flex=%d",
        origin_city, destination_country, destination_city,
        req.departure_date, req.date_flexibility_days,
    )

    try:
        engine = _get_flight_engine()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Motor de busca indisponível. Verifique os logs.",
        )

    results = await engine.search(
        origin_city=origin_city,
        destination_country=destination_country,
        destination_city=destination_city,
        departure_date=req.departure_date,
        return_date=req.return_date,
        passengers=req.passengers,
        date_flexibility_days=req.date_flexibility_days,
        currency="BRL",
    )

    cheapest = results[0] if results else None

    if not has_key and not results:
        msg = (
            "Configure AMADEUS_API_KEY e AMADEUS_API_SECRET no arquivo .env "
            "para buscar preços reais. Registro gratuito em developers.amadeus.com"
        )
    elif results:
        total = len(results)
        msg = f"{total} voo(s) encontrado(s) | ranqueados por preço (menor para maior)"
        if req.date_flexibility_days > 0:
            msg += f" | inclui ±{req.date_flexibility_days} dias de flexibilidade"
    else:
        msg = "Nenhum voo encontrado para os parâmetros informados."

    return FlightSearchResponse(
        results=results,
        total=len(results),
        cheapest_price=float(cheapest["preco"]) if cheapest else None,
        cheapest_destination=cheapest.get("destino_cidade") if cheapest else None,
        cheapest_date=cheapest.get("data_ida_real") if cheapest else None,
        has_api_key=has_key,
        message=msg,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_country(destination: str) -> str:
    """Extrai país de string como 'Miami, EUA' → 'EUA'."""
    parts = destination.split(",")
    if len(parts) >= 2:
        return parts[-1].strip()
    dest_lower = destination.lower()
    if any(w in dest_lower for w in ["eua", "usa", "united states", "estados unidos"]):
        return "EUA"
    if any(w in dest_lower for w in ["portugal", "lisboa", "porto"]):
        return "Portugal"
    if any(w in dest_lower for w in ["argentina", "buenos aires"]):
        return "Argentina"
    return destination


def _extract_city(destination: str) -> str:
    """Extrai cidade de string como 'Miami, EUA' → 'Miami'."""
    parts = destination.split(",")
    if len(parts) >= 2:
        city = parts[0].strip()
        if city.lower() in ("qualquer cidade do pais", "qualquer cidade", "any city", ""):
            return ""
        return city
    return ""
