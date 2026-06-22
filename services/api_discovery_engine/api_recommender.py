"""
APIRecommender — recomenda APIs públicas como alternativa ao scraping.

Combina o catálogo curado interno (KNOWN_APIS) com resultados do PublicAPIIndexer
para oferecer as melhores alternativas antes de iniciar o scraping.
"""

import logging
from typing import Any

from .api_matcher import APIMatcher
from .public_api_indexer import PublicAPIIndexer

logger = logging.getLogger(__name__)


class APIRecommender:
    """
    Recomenda APIs públicas relevantes dado uma URL ou tipo de busca.

    Catálogo curado interno para os casos de uso mais comuns da plataforma:
    - Passagens aéreas / Flights
    - Notícias / News
    - Empregos / Jobs
    - Leads / Contatos

    Também integra com o PublicAPIIndexer para enriquecer as recomendações
    com o catálogo completo do repositório public-apis.

    Exemplo de uso
    --------------
    recommender = APIRecommender()
    apis = await recommender.recommend("https://skyscanner.net", search_type="flights")
    for api in apis:
        print(api["name"], api["url"], api["free_tier"])
    """

    # ------------------------------------------------------------------
    # Catálogo curado interno
    # ------------------------------------------------------------------

    KNOWN_APIS: dict[str, list[dict]] = {
        "flights": [
            {
                "name": "Aviationstack",
                "url": "https://aviationstack.com/",
                "docs_url": "https://aviationstack.com/documentation",
                "description": "Dados de voos em tempo real, rotas, aeroportos e companhias aéreas. 500 req/mês grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Unknown",
                "category": "flights",
                "example": "GET https://api.aviationstack.com/v1/flights?access_key=KEY&dep_iata=GRU",
                "rate_limit": "500 requests/month (free)",
            },
            {
                "name": "Amadeus",
                "url": "https://developers.amadeus.com/",
                "docs_url": "https://developers.amadeus.com/self-service",
                "description": "API completa de viagens: voos, hotéis, atividades. Sandbox gratuito.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "flights",
                "example": "GET https://test.api.amadeus.com/v2/shopping/flight-offers",
                "rate_limit": "2000 requests/month (sandbox)",
            },
            {
                "name": "AviationEdge",
                "url": "https://aviation-edge.com/",
                "docs_url": "https://aviation-edge.com/developers/",
                "description": "Dados de voos, rastreamento em tempo real, status de aeroportos.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Unknown",
                "category": "flights",
                "example": "GET https://aviation-edge.com/v2/public/flights?key=KEY&depIata=GRU",
                "rate_limit": "100 requests/month (free trial)",
            },
            {
                "name": "OpenSky Network",
                "url": "https://openskynetwork.github.io/opensky-api/",
                "docs_url": "https://openskynetwork.github.io/opensky-api/rest.html",
                "description": "Dados ADS-B de aeronaves em tempo real. Completamente gratuito.",
                "free_tier": True,
                "key_required": False,
                "https": True,
                "cors": "Yes",
                "category": "flights",
                "example": "GET https://opensky-network.org/api/states/all",
                "rate_limit": "Unlimited (anônimo: 100 req/dia)",
            },
        ],
        "news": [
            {
                "name": "NewsAPI",
                "url": "https://newsapi.org/",
                "docs_url": "https://newsapi.org/docs",
                "description": "Artigos de notícias de 150k fontes. 100 req/dia grátis (developer plan).",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "news",
                "example": "GET https://newsapi.org/v2/top-headlines?country=br&apiKey=KEY",
                "rate_limit": "100 requests/day (free)",
            },
            {
                "name": "GNews",
                "url": "https://gnews.io/",
                "docs_url": "https://gnews.io/docs/v4",
                "description": "Notícias indexadas do Google News. 100 req/dia grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "news",
                "example": "GET https://gnews.io/api/v4/top-headlines?country=br&token=KEY",
                "rate_limit": "100 requests/day (free)",
            },
            {
                "name": "TheNewsAPI",
                "url": "https://www.thenewsapi.com/",
                "docs_url": "https://www.thenewsapi.com/documentation",
                "description": "Notícias categorizadas com NLP. 3 req/min grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "news",
                "example": "GET https://api.thenewsapi.com/v1/news/top?api_token=KEY&locale=br",
                "rate_limit": "3 requests/minute, 100/day (free)",
            },
            {
                "name": "MediaStack",
                "url": "https://mediastack.com/",
                "docs_url": "https://mediastack.com/documentation",
                "description": "500+ fontes de notícias globais. 500 req/mês grátis.",
                "free_tier": True,
                "key_required": True,
                "https": False,  # HTTPS só no plano pago
                "cors": "Unknown",
                "category": "news",
                "example": "GET http://api.mediastack.com/v1/news?access_key=KEY&countries=br",
                "rate_limit": "500 requests/month (free)",
            },
        ],
        "jobs": [
            {
                "name": "Arbeitnow",
                "url": "https://www.arbeitnow.com/api/job-board-api",
                "docs_url": "https://www.arbeitnow.com/api/job-board-api",
                "description": "API pública de vagas de emprego europeu. 100% gratuita, sem key.",
                "free_tier": True,
                "key_required": False,
                "https": True,
                "cors": "Yes",
                "category": "jobs",
                "example": "GET https://www.arbeitnow.com/api/job-board-api",
                "rate_limit": "Unlimited",
            },
            {
                "name": "The Muse",
                "url": "https://www.themuse.com/developers/api/v2",
                "docs_url": "https://www.themuse.com/developers/api/v2",
                "description": "Vagas de emprego com perfil de cultura de empresas. Gratuita, sem key.",
                "free_tier": True,
                "key_required": False,
                "https": True,
                "cors": "Yes",
                "category": "jobs",
                "example": "GET https://www.themuse.com/api/public/jobs",
                "rate_limit": "Generous (anonymous)",
            },
            {
                "name": "Jooble",
                "url": "https://jooble.org/api/about",
                "docs_url": "https://jooble.org/api/about",
                "description": "Motor de busca de vagas globais com API. Key gratuita mediante cadastro.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Unknown",
                "category": "jobs",
                "example": "POST https://jooble.org/api/{key} body: {keywords: 'python', location: 'São Paulo'}",
                "rate_limit": "500 requests/day (free)",
            },
            {
                "name": "Reed API",
                "url": "https://www.reed.co.uk/developers/jobseeker",
                "docs_url": "https://www.reed.co.uk/developers/jobseeker",
                "description": "API de vagas do Reino Unido. Key gratuita.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Unknown",
                "category": "jobs",
                "example": "GET https://www.reed.co.uk/api/1.0/search?keywords=python",
                "rate_limit": "Limited (free)",
            },
        ],
        "leads": [
            {
                "name": "Hunter.io",
                "url": "https://hunter.io/api",
                "docs_url": "https://hunter.io/api-documentation/v2",
                "description": "Encontra emails profissionais por domínio. 25 buscas/mês grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "leads",
                "example": "GET https://api.hunter.io/v2/domain-search?domain=exemplo.com.br&api_key=KEY",
                "rate_limit": "25 requests/month (free)",
            },
            {
                "name": "Apollo API",
                "url": "https://developer.apollo.io/",
                "docs_url": "https://apolloio.github.io/apollo-api-docs/",
                "description": "Enriquecimento de leads B2B: emails, telefones, LinkedIn. Trial gratuito.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "leads",
                "example": "POST https://api.apollo.io/v1/people/match",
                "rate_limit": "600 credits/month (free)",
            },
            {
                "name": "Clearbit",
                "url": "https://clearbit.com/",
                "docs_url": "https://dashboard.clearbit.com/docs",
                "description": "Enriquecimento de dados de empresas e pessoas por email/domínio.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "leads",
                "example": "GET https://company.clearbit.com/v2/companies/find?domain=exemplo.com",
                "rate_limit": "50 requests/month (free trial)",
            },
        ],
        "weather": [
            {
                "name": "Open-Meteo",
                "url": "https://open-meteo.com/",
                "docs_url": "https://open-meteo.com/en/docs",
                "description": "API de clima open-source. Completamente gratuita, sem key.",
                "free_tier": True,
                "key_required": False,
                "https": True,
                "cors": "Yes",
                "category": "weather",
                "example": "GET https://api.open-meteo.com/v1/forecast?latitude=-23.5&longitude=-46.6&hourly=temperature_2m",
                "rate_limit": "Unlimited",
            },
            {
                "name": "OpenWeatherMap",
                "url": "https://openweathermap.org/api",
                "docs_url": "https://openweathermap.org/api/one-call-3",
                "description": "Clima atual, previsão 5 dias, dados históricos. 1000 req/dia grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "weather",
                "example": "GET https://api.openweathermap.org/data/2.5/weather?q=São Paulo&appid=KEY",
                "rate_limit": "1000 requests/day (free)",
            },
        ],
        "finance": [
            {
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/",
                "docs_url": "https://www.alphavantage.co/documentation/",
                "description": "Dados de ações, forex, crypto. 25 req/dia grátis.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "finance",
                "example": "GET https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=PETR4.SAO&apikey=KEY",
                "rate_limit": "25 requests/day (free)",
            },
            {
                "name": "Brapi (B3)",
                "url": "https://brapi.dev/",
                "docs_url": "https://brapi.dev/docs",
                "description": "API brasileira para dados da B3 (Bovespa). Gratuita com limites.",
                "free_tier": True,
                "key_required": True,
                "https": True,
                "cors": "Yes",
                "category": "finance",
                "example": "GET https://brapi.dev/api/quote/PETR4?token=KEY",
                "rate_limit": "Freemium",
            },
        ],
    }

    def __init__(
        self,
        use_public_index: bool = True,
        indexer: PublicAPIIndexer | None = None,
    ) -> None:
        self.use_public_index = use_public_index
        self._indexer = indexer or PublicAPIIndexer()
        self._matcher = APIMatcher()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def recommend(
        self,
        url: str,
        search_type: str = "",
        text: str = "",
        include_public_index: bool = True,
        limit: int = 10,
    ) -> list[dict]:
        """
        Retorna lista de APIs recomendadas para a URL/tipo de busca.

        Parâmetros
        ----------
        url : str
            URL que seria scraped.
        search_type : str
            Tipo de busca: "flights", "news", "jobs", "leads", "weather", "finance".
        text : str
            Texto livre descrevendo o que quer coletar.
        include_public_index : bool
            Se True, complementa com resultados do catálogo public-apis.
        limit : int
            Máximo de resultados.

        Retorno
        -------
        list[dict] com APIs recomendadas, ordenadas por relevância.
        """
        # 1. Detecta categorias relevantes
        categories: list[str] = []

        if search_type:
            categories.extend(self._matcher.match_search_type(search_type))

        if url:
            categories.extend(self._matcher.match_url(url))

        if text:
            categories.extend(self._matcher.match_keywords(text))

        # Remove duplicatas mantendo ordem
        seen: set = set()
        categories = [c for c in categories if not (c in seen or seen.add(c))]  # type: ignore

        if not categories and search_type:
            categories = [search_type]

        logger.info(
            "APIRecommender.recommend() | url=%s | search_type=%s | categorias=%s",
            url, search_type, categories,
        )

        # 2. Busca no catálogo curado
        curated = self._get_curated(categories)

        # 3. Busca no índice público (opcional)
        public_results: list[dict] = []
        if include_public_index and self.use_public_index:
            public_results = await self._get_from_index(categories, curated)

        # 4. Merge e rank
        all_results = self._merge_and_rank(curated, public_results, categories, url)

        return all_results[:limit]

    async def recommend_for_job(self, job: dict) -> list[dict]:
        """
        Atalho para recomendar APIs para um job dict.
        Usa job["url"] e job["search_type"].
        """
        return await self.recommend(
            url=job.get("url", ""),
            search_type=job.get("search_type", ""),
        )

    def get_categories(self) -> list[str]:
        """Retorna todas as categorias do catálogo curado."""
        return list(self.KNOWN_APIS.keys())

    def get_by_category(self, category: str) -> list[dict]:
        """Retorna APIs curadas de uma categoria específica."""
        return self.KNOWN_APIS.get(category, [])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_curated(self, categories: list[str]) -> list[dict]:
        """Busca no catálogo curado por categorias."""
        results: list[dict] = []
        seen_names: set = set()

        for cat in categories:
            for api in self.KNOWN_APIS.get(cat, []):
                if api["name"] not in seen_names:
                    results.append({**api, "_source": "curated", "_category": cat})
                    seen_names.add(api["name"])

        return results

    async def _get_from_index(
        self, categories: list[str], already_found: list[dict]
    ) -> list[dict]:
        """Busca complementar no PublicAPIIndexer."""
        try:
            # Só busca se o índice tiver dados
            count = self._indexer._count_indexed()
            if count == 0:
                return []

            found_names = {a["name"].lower() for a in already_found}
            results: list[dict] = []

            for cat in categories[:3]:  # Limita para não sobrecarregar
                apis = self._indexer.search(cat, limit=10)
                for api in apis:
                    if api["name"].lower() not in found_names:
                        results.append({**api, "_source": "public_index", "_category": cat})
                        found_names.add(api["name"].lower())

            return results
        except Exception as exc:
            logger.warning("APIRecommender._get_from_index(): %s", exc)
            return []

    def _merge_and_rank(
        self,
        curated: list[dict],
        public: list[dict],
        categories: list[str],
        url: str,
    ) -> list[dict]:
        """Combina e ranqueia resultados por relevância."""
        all_apis = curated + public

        # Calcula score para cada API
        for api in all_apis:
            base_score = self._matcher.score_relevance(api, categories, url)
            # Bônus para catálogo curado
            if api.get("_source") == "curated":
                base_score += 0.3
            api["_relevance_score"] = min(round(base_score, 3), 1.0)

        # Ordena por relevância
        all_apis.sort(key=lambda a: a["_relevance_score"], reverse=True)

        # Remove campos internos antes de retornar
        clean: list[dict] = []
        for api in all_apis:
            entry = {k: v for k, v in api.items() if not k.startswith("_")}
            entry["relevance_score"] = api["_relevance_score"]
            clean.append(entry)

        return clean
