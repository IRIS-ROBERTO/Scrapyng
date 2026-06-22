"""
Mapeamento de cidades para códigos IATA de aeroportos.
Inclui dados de rotas típicas GRU→EUA: preços estimados em BRL, companhias, horários.
"""

from __future__ import annotations

# Aeroportos dos EUA com dados realistas para rotas a partir de GRU (São Paulo)
# price_min/max: estimativa de tarifa ida+volta em BRL (2026, alta temporada)
# airlines: companhias que operam a rota diretamente ou com escala preferencial
# stops: 0=direto disponível, 1=1 escala
US_AIRPORTS: list[dict] = [
    {
        "iata": "MIA", "city": "Miami",         "state": "FL", "country": "EUA",
        "price_min": 2800, "price_max": 5500,
        "airlines": ["LATAM", "American Airlines", "Azul"],
        "flight_time": "9h 30min", "stops": 0,
        "dep_time": "23:55", "arr_time": "07:25",
    },
    {
        "iata": "JFK", "city": "Nova York",      "state": "NY", "country": "EUA",
        "price_min": 3200, "price_max": 6500,
        "airlines": ["LATAM", "American Airlines", "TAP", "Air France"],
        "flight_time": "10h 15min", "stops": 0,
        "dep_time": "22:40", "arr_time": "08:55",
    },
    {
        "iata": "EWR", "city": "Newark/NY",      "state": "NJ", "country": "EUA",
        "price_min": 3100, "price_max": 6200,
        "airlines": ["United Airlines", "TAP", "Air France"],
        "flight_time": "10h 20min", "stops": 0,
        "dep_time": "21:30", "arr_time": "07:50",
    },
    {
        "iata": "MCO", "city": "Orlando",        "state": "FL", "country": "EUA",
        "price_min": 2900, "price_max": 5800,
        "airlines": ["LATAM", "American Airlines", "Azul"],
        "flight_time": "9h 45min", "stops": 0,
        "dep_time": "22:30", "arr_time": "08:15",
    },
    {
        "iata": "FLL", "city": "Fort Lauderdale","state": "FL", "country": "EUA",
        "price_min": 2750, "price_max": 5400,
        "airlines": ["LATAM", "Spirit", "American Airlines"],
        "flight_time": "9h 35min", "stops": 0,
        "dep_time": "23:10", "arr_time": "08:45",
    },
    {
        "iata": "IAH", "city": "Houston",        "state": "TX", "country": "EUA",
        "price_min": 2700, "price_max": 5200,
        "airlines": ["United Airlines", "Copa Airlines"],
        "flight_time": "9h 00min", "stops": 1,
        "dep_time": "06:30", "arr_time": "17:30",
    },
    {
        "iata": "ATL", "city": "Atlanta",        "state": "GA", "country": "EUA",
        "price_min": 3000, "price_max": 5900,
        "airlines": ["Delta Air Lines", "LATAM"],
        "flight_time": "10h 00min", "stops": 1,
        "dep_time": "08:00", "arr_time": "20:00",
    },
    {
        "iata": "ORD", "city": "Chicago",        "state": "IL", "country": "EUA",
        "price_min": 3300, "price_max": 6800,
        "airlines": ["United Airlines", "American Airlines"],
        "flight_time": "12h 30min", "stops": 1,
        "dep_time": "07:00", "arr_time": "21:30",
    },
    {
        "iata": "DFW", "city": "Dallas",         "state": "TX", "country": "EUA",
        "price_min": 3200, "price_max": 6200,
        "airlines": ["American Airlines", "LATAM"],
        "flight_time": "11h 00min", "stops": 1,
        "dep_time": "09:00", "arr_time": "22:00",
    },
    {
        "iata": "LAX", "city": "Los Angeles",    "state": "CA", "country": "EUA",
        "price_min": 3800, "price_max": 7500,
        "airlines": ["LATAM", "American Airlines", "Delta Air Lines"],
        "flight_time": "14h 00min", "stops": 1,
        "dep_time": "20:00", "arr_time": "12:00",
    },
    {
        "iata": "SFO", "city": "San Francisco",  "state": "CA", "country": "EUA",
        "price_min": 4200, "price_max": 8500,
        "airlines": ["United Airlines", "LATAM", "Delta Air Lines"],
        "flight_time": "15h 30min", "stops": 1,
        "dep_time": "19:30", "arr_time": "13:00",
    },
    {
        "iata": "IAD", "city": "Washington DC",  "state": "DC", "country": "EUA",
        "price_min": 3000, "price_max": 5800,
        "airlines": ["United Airlines", "American Airlines", "TAP"],
        "flight_time": "10h 30min", "stops": 0,
        "dep_time": "22:00", "arr_time": "08:30",
    },
    {
        "iata": "BOS", "city": "Boston",         "state": "MA", "country": "EUA",
        "price_min": 3400, "price_max": 6500,
        "airlines": ["LATAM", "TAP", "American Airlines"],
        "flight_time": "10h 45min", "stops": 1,
        "dep_time": "21:00", "arr_time": "09:45",
    },
    {
        "iata": "LAS", "city": "Las Vegas",      "state": "NV", "country": "EUA",
        "price_min": 4000, "price_max": 8000,
        "airlines": ["American Airlines", "United Airlines"],
        "flight_time": "14h 30min", "stops": 1,
        "dep_time": "18:00", "arr_time": "10:30",
    },
    {
        "iata": "SEA", "city": "Seattle",        "state": "WA", "country": "EUA",
        "price_min": 4500, "price_max": 9000,
        "airlines": ["Delta Air Lines", "United Airlines"],
        "flight_time": "16h 00min", "stops": 1,
        "dep_time": "17:30", "arr_time": "11:30",
    },
    {
        "iata": "DEN", "city": "Denver",         "state": "CO", "country": "EUA",
        "price_min": 3800, "price_max": 7200,
        "airlines": ["United Airlines", "American Airlines"],
        "flight_time": "13h 00min", "stops": 1,
        "dep_time": "08:30", "arr_time": "23:30",
    },
    {
        "iata": "TPA", "city": "Tampa",          "state": "FL", "country": "EUA",
        "price_min": 2850, "price_max": 5500,
        "airlines": ["American Airlines", "LATAM"],
        "flight_time": "9h 50min", "stops": 1,
        "dep_time": "10:00", "arr_time": "21:50",
    },
    {
        "iata": "PHX", "city": "Phoenix",        "state": "AZ", "country": "EUA",
        "price_min": 3700, "price_max": 7000,
        "airlines": ["American Airlines", "United Airlines"],
        "flight_time": "13h 30min", "stops": 1,
        "dep_time": "11:00", "arr_time": "00:30",
    },
    {
        "iata": "MSP", "city": "Minneapolis",    "state": "MN", "country": "EUA",
        "price_min": 3600, "price_max": 7000,
        "airlines": ["Delta Air Lines", "United Airlines"],
        "flight_time": "13h 45min", "stops": 1,
        "dep_time": "09:30", "arr_time": "01:15",
    },
    {
        "iata": "SAN", "city": "San Diego",      "state": "CA", "country": "EUA",
        "price_min": 4000, "price_max": 7800,
        "airlines": ["American Airlines", "United Airlines"],
        "flight_time": "14h 15min", "stops": 1,
        "dep_time": "19:00", "arr_time": "11:15",
    },
]

# Índice IATA → dados do aeroporto
US_AIRPORT_BY_IATA: dict[str, dict] = {ap["iata"]: ap for ap in US_AIRPORTS}

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
US_CITY_TO_IATA: dict[str, str] = {}
for ap in US_AIRPORTS:
    city_lower = ap["city"].lower()
    US_CITY_TO_IATA[city_lower] = ap["iata"]
    US_CITY_TO_IATA[city_lower.replace(" ", "-")] = ap["iata"]
    US_CITY_TO_IATA[ap["iata"].lower()] = ap["iata"]

US_CITY_TO_IATA.update({
    "nova york":        "JFK",
    "new york":         "JFK",
    "new-york":         "JFK",
    "new york/newark":  "EWR",
    "los angeles":      "LAX",
    "los-angeles":      "LAX",
    "miami":            "MIA",
    "orlando":          "MCO",
    "chicago":          "ORD",
    "san francisco":    "SFO",
    "san-francisco":    "SFO",
    "dallas":           "DFW",
    "atlanta":          "ATL",
    "boston":           "BOS",
    "seattle":          "SEA",
    "las vegas":        "LAS",
    "las-vegas":        "LAS",
    "houston":          "IAH",
    "phoenix":          "PHX",
    "washington":       "IAD",
    "washington dc":    "IAD",
    "denver":           "DEN",
    "minneapolis":      "MSP",
    "detroit":          "DTW",
    "san diego":        "SAN",
    "san-diego":        "SAN",
    "tampa":            "TPA",
    "fort lauderdale":  "FLL",
    "fort-lauderdale":  "FLL",
})


def city_to_iata(city_name: str, country: str = "") -> str | None:
    """Converte nome de cidade para código IATA."""
    key = city_name.strip().lower()

    if "eua" in country.lower() or "united" in country.lower() or "usa" in country.lower():
        return US_CITY_TO_IATA.get(key)

    code = BRAZIL_AIRPORTS.get(key)
    if code:
        return code

    for k, v in BRAZIL_AIRPORTS.items():
        if k in key or key in k:
            return v

    return None


def get_us_airports_for_search(specific_city: str = "") -> list[dict]:
    """
    Retorna aeroportos dos EUA para busca.
    Se cidade específica, retorna só ela. Senão todos.
    """
    if specific_city:
        key = specific_city.strip().lower()
        iata = US_CITY_TO_IATA.get(key)
        if iata:
            return [ap for ap in US_AIRPORTS if ap["iata"] == iata]
    return US_AIRPORTS


def get_airport_info(iata: str) -> dict:
    """Retorna dados do aeroporto ou dict vazio."""
    return US_AIRPORT_BY_IATA.get(iata.upper(), {})
