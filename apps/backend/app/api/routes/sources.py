from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser

router = APIRouter(prefix="/sources", tags=["Sources"])

# Static catalog of publicly available free APIs for data sourcing
FREE_APIS = [
    {
        "id": "open-meteo",
        "name": "Open-Meteo",
        "category": "weather",
        "description": "Free weather API – no key required",
        "base_url": "https://api.open-meteo.com/v1",
        "docs": "https://open-meteo.com/en/docs",
        "auth_required": False,
        "rate_limit": "10,000 req/day",
    },
    {
        "id": "exchangerate-api",
        "name": "ExchangeRate-API",
        "category": "finance",
        "description": "Currency exchange rates – free tier available",
        "base_url": "https://open.er-api.com/v6",
        "docs": "https://www.exchangerate-api.com/docs",
        "auth_required": False,
        "rate_limit": "1,500 req/month (free tier)",
    },
    {
        "id": "news-api",
        "name": "NewsAPI.org",
        "category": "news",
        "description": "News headlines and articles from 80,000+ sources",
        "base_url": "https://newsapi.org/v2",
        "docs": "https://newsapi.org/docs",
        "auth_required": True,
        "rate_limit": "100 req/day (free)",
    },
    {
        "id": "pokeapi",
        "name": "PokéAPI",
        "category": "entertainment",
        "description": "RESTful Pokémon API – fully public",
        "base_url": "https://pokeapi.co/api/v2",
        "docs": "https://pokeapi.co/docs/v2",
        "auth_required": False,
        "rate_limit": "100 req/min",
    },
    {
        "id": "github-api",
        "name": "GitHub REST API",
        "category": "development",
        "description": "GitHub repositories, issues, users, and more",
        "base_url": "https://api.github.com",
        "docs": "https://docs.github.com/en/rest",
        "auth_required": False,
        "rate_limit": "60 req/hr unauthenticated / 5,000 authenticated",
    },
    {
        "id": "openlibrary",
        "name": "Open Library",
        "category": "books",
        "description": "Books, authors and covers from Internet Archive",
        "base_url": "https://openlibrary.org/api",
        "docs": "https://openlibrary.org/developers/api",
        "auth_required": False,
        "rate_limit": "None documented",
    },
    {
        "id": "restcountries",
        "name": "REST Countries",
        "category": "geography",
        "description": "Country data including flags, languages, currencies",
        "base_url": "https://restcountries.com/v3.1",
        "docs": "https://restcountries.com",
        "auth_required": False,
        "rate_limit": "None",
    },
    {
        "id": "ibge-sidra",
        "name": "IBGE SIDRA",
        "category": "statistics-br",
        "description": "Brazilian statistics from IBGE – GDP, population, economy",
        "base_url": "https://servicodados.ibge.gov.br/api/v3",
        "docs": "https://servicodados.ibge.gov.br/api/docs",
        "auth_required": False,
        "rate_limit": "None documented",
    },
]


@router.get("/apis", summary="List available free public APIs")
async def list_apis(
    current_user: CurrentUser,
    category: str | None = None,
) -> dict:
    """Return catalog of free public APIs that can be used as data sources."""
    apis = FREE_APIS
    if category:
        apis = [a for a in apis if a["category"] == category]
    categories = sorted({a["category"] for a in FREE_APIS})
    return {
        "total": len(apis),
        "categories": categories,
        "apis": apis,
    }
