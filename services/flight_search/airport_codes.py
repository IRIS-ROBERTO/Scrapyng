"""
Mapeamento de cidades para códigos IATA de aeroportos.
"""

from __future__ import annotations

# Aeroportos dos EUA — todos pesquisados quando destino = "qualquer cidade"
US_AIRPORTS: list[dict] = [
    {"iata": "JFK", "city": "Nova York",      "state": "NY", "country": "EUA"},
    {"iata": "EWR", "city": "Newark/NY",       "state": "NJ", "country": "EUA"},
    {"iata": "LAX", "city": "Los Angeles",     "state": "CA", "country": "EUA"},
    {"iata": "MIA", "city": "Miami",           "state": "FL", "country": "EUA"},
    {"iata": "MCO", "city": "Orlando",         "state": "FL", "country": "EUA"},
    {"iata": "ORD", "city": "Chicago",         "state": "IL", "country": "EUA"},
    {"iata": "SFO", "city": "San Francisco",   "state": "CA", "country": "EUA"},
    {"iata": "DFW", "city": "Dallas",          "state": "TX", "country": "EUA"},
    {"iata": "ATL", "city": "Atlanta",         "state": "GA", "country": "EUA"},
    {"iata": "BOS", "city": "Boston",          "state": "MA", "country": "EUA"},
    {"iata": "SEA", "city": "Seattle",         "state": "WA", "country": "EUA"},
    {"iata": "LAS", "city": "Las Vegas",       "state": "NV", "country": "EUA"},
    {"iata": "IAH", "city": "Houston",         "state": "TX", "country": "EUA"},
    {"iata": "PHX", "city": "Phoenix",         "state": "AZ", "country": "EUA"},
    {"iata": "IAD", "city": "Washington DC",   "state": "DC", "country": "EUA"},
    {"iata": "DEN", "city": "Denver",          "state": "CO", "country": "EUA"},
    {"iata": "MSP", "city": "Minneapolis",     "state": "MN", "country": "EUA"},
    {"iata": "DTW", "city": "Detroit",         "state": "MI", "country": "EUA"},
    {"iata": "SAN", "city": "San Diego",       "state": "CA", "country": "EUA"},
    {"iata": "TPA", "city": "Tampa",           "state": "FL", "country": "EUA"},
]

# Aeroportos do Brasil
BRAZIL_AIRPORTS: dict[str, str] = {
    "sao paulo":        "GRU",
    "guarulhos":        "GRU",
    "sao-paulo":        "GRU",
    "campinas":         "VCP",
    "rio de janeiro":   "GIG",
    "rio-de-janeiro":   "GIG",
    "brasilia":         "BSB",
    "belo horizonte":   "CNF",
    "belo-horizonte":   "CNF",
    "salvador":         "SSA",
    "fortaleza":        "FOR",
    "recife":           "REC",
    "manaus":           "MAO",
    "porto alegre":     "POA",
    "porto-alegre":     "POA",
    "curitiba":         "CWB",
    "florianopolis":    "FLN",
    "belem":            "BEL",
    "natal":            "NAT",
    "maceio":           "MCZ",
}

# Aeroportos do destino EUA por nome/slug de cidade
US_CITY_TO_IATA: dict[str, str] = {city.lower(): ap["iata"] for ap in US_AIRPORTS for city in [
    ap["city"].lower(),
    ap["city"].lower().replace(" ", "-"),
    ap["iata"].lower(),
]}
US_CITY_TO_IATA.update({
    "nova york":     "JFK",
    "new york":      "JFK",
    "new-york":      "JFK",
    "new york/newark": "EWR",
    "los angeles":   "LAX",
    "los-angeles":   "LAX",
    "miami":         "MIA",
    "orlando":       "MCO",
    "chicago":       "ORD",
    "san francisco": "SFO",
    "san-francisco": "SFO",
    "dallas":        "DFW",
    "atlanta":       "ATL",
    "boston":        "BOS",
    "seattle":       "SEA",
    "las vegas":     "LAS",
    "las-vegas":     "LAS",
    "houston":       "IAH",
    "phoenix":       "PHX",
    "washington":    "IAD",
    "washington dc": "IAD",
    "denver":        "DEN",
    "minneapolis":   "MSP",
    "detroit":       "DTW",
    "san diego":     "SAN",
    "san-diego":     "SAN",
    "tampa":         "TPA",
})


def city_to_iata(city_name: str, country: str = "") -> str | None:
    """Converte nome de cidade para código IATA."""
    key = city_name.strip().lower()

    # EUA
    if "eua" in country.lower() or "united" in country.lower() or "usa" in country.lower():
        return US_CITY_TO_IATA.get(key)

    # Brasil
    code = BRAZIL_AIRPORTS.get(key)
    if code:
        return code

    # Tenta busca parcial no Brasil
    for k, v in BRAZIL_AIRPORTS.items():
        if k in key or key in k:
            return v

    return None


def get_us_airports_for_search(specific_city: str = "") -> list[dict]:
    """
    Retorna lista de aeroportos dos EUA para busca.
    Se cidade específica informada, retorna apenas aquela.
    Senão retorna todos.
    """
    if specific_city:
        key = specific_city.strip().lower()
        iata = US_CITY_TO_IATA.get(key)
        if iata:
            return [ap for ap in US_AIRPORTS if ap["iata"] == iata]
    return US_AIRPORTS
