"""
APIMatcher — faz match entre URL/tema de interesse e APIs públicas disponíveis.

Estratégias de matching:
1. Match por domínio da URL (ex: booking.com → travel APIs)
2. Match por palavras-chave no tema (ex: "voos" → flights APIs)
3. Match por categoria do catálogo public-apis
4. Score de relevância para ranqueamento
"""

import logging
import re
from urllib.parse import urlparse
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapeamentos de domínios conhecidos → categorias de APIs
# ---------------------------------------------------------------------------

_DOMAIN_TO_CATEGORY: dict[str, list[str]] = {
    # Viagens / Passagens
    "booking.com": ["travel", "hotels"],
    "airbnb.com": ["travel", "hotels"],
    "kayak.com": ["travel", "flights"],
    "skyscanner.net": ["travel", "flights"],
    "google.com/flights": ["flights"],
    "latam.com": ["flights", "airlines"],
    "azul.com.br": ["flights", "airlines"],
    "gol.com.br": ["flights", "airlines"],
    "avianca.com": ["flights", "airlines"],
    "flightaware.com": ["flights", "aviation"],
    # Notícias
    "g1.globo.com": ["news"],
    "uol.com.br": ["news"],
    "folha.uol.com.br": ["news"],
    "estadao.com.br": ["news"],
    "bbc.com": ["news"],
    "reuters.com": ["news"],
    "cnn.com": ["news"],
    # Empregos
    "linkedin.com": ["jobs"],
    "indeed.com": ["jobs"],
    "glassdoor.com": ["jobs"],
    "catho.com.br": ["jobs"],
    "infojobs.com.br": ["jobs"],
    "vagas.com.br": ["jobs"],
    # E-commerce / Produtos
    "amazon.com": ["ecommerce", "shopping"],
    "mercadolivre.com.br": ["ecommerce", "shopping"],
    "shopee.com.br": ["ecommerce", "shopping"],
    # Clima
    "weather.com": ["weather"],
    "climatempo.com.br": ["weather"],
    # Finanças
    "b3.com.br": ["finance", "stocks"],
    "bovespa.com.br": ["finance", "stocks"],
    "investing.com": ["finance", "stocks"],
    # Leads / Empresas
    "linkedin.com/company": ["leads", "companies"],
    "cnpj.info": ["leads", "companies"],
}

# Palavras-chave em português e inglês → categoria
_KEYWORD_TO_CATEGORY: dict[str, list[str]] = {
    # Viagens
    "voo": ["flights", "travel"],
    "voos": ["flights", "travel"],
    "passagem": ["flights", "travel"],
    "passagens": ["flights", "travel"],
    "flight": ["flights", "travel"],
    "flights": ["flights", "travel"],
    "airline": ["flights", "travel"],
    "aviao": ["flights", "travel"],
    "aeroporto": ["flights", "aviation"],
    "hotel": ["hotels", "travel"],
    "hospedagem": ["hotels", "travel"],
    # Notícias
    "noticia": ["news"],
    "noticias": ["news"],
    "news": ["news"],
    "headline": ["news"],
    "article": ["news"],
    # Empregos
    "emprego": ["jobs"],
    "empregos": ["jobs"],
    "vaga": ["jobs"],
    "vagas": ["jobs"],
    "job": ["jobs"],
    "jobs": ["jobs"],
    "career": ["jobs"],
    "recrutamento": ["jobs"],
    # Leads / Contatos
    "lead": ["leads", "email"],
    "leads": ["leads", "email"],
    "email": ["leads", "email"],
    "contato": ["leads"],
    "empresa": ["leads", "companies"],
    "empresas": ["leads", "companies"],
    # Clima
    "clima": ["weather"],
    "tempo": ["weather"],
    "weather": ["weather"],
    "forecast": ["weather"],
    # Finanças
    "acao": ["finance", "stocks"],
    "acoes": ["finance", "stocks"],
    "bolsa": ["finance", "stocks"],
    "stock": ["finance", "stocks"],
    "crypto": ["cryptocurrency"],
    "bitcoin": ["cryptocurrency"],
    # E-commerce
    "produto": ["ecommerce", "shopping"],
    "preco": ["ecommerce", "shopping"],
    "loja": ["ecommerce", "shopping"],
}


class APIMatcher:
    """
    Faz match entre URL/tema de busca e categorias de APIs disponíveis.

    Exemplo de uso
    --------------
    matcher = APIMatcher()
    categories = matcher.match_url("https://skyscanner.net/routes/bra/usa")
    # → ["flights", "travel"]

    categories = matcher.match_keywords("vagas de emprego em SP")
    # → ["jobs"]
    """

    def match_url(self, url: str) -> list[str]:
        """
        Detecta categorias de APIs relevantes com base na URL.

        Parâmetros
        ----------
        url : str
            URL do site que seria scraped.

        Retorno
        -------
        list[str] : categorias detectadas (pode ser vazia).
        """
        categories: set[str] = set()
        url_lower = url.lower()

        for domain, cats in _DOMAIN_TO_CATEGORY.items():
            if domain in url_lower:
                categories.update(cats)

        # Parsing do domínio para match parcial
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower().replace("www.", "")
            for domain, cats in _DOMAIN_TO_CATEGORY.items():
                if netloc in domain or domain in netloc:
                    categories.update(cats)
        except Exception:
            pass

        # Keywords na URL path
        path_keywords = re.findall(r"[a-z]{3,}", url_lower)
        for kw in path_keywords:
            if kw in _KEYWORD_TO_CATEGORY:
                categories.update(_KEYWORD_TO_CATEGORY[kw])

        return list(categories)

    def match_keywords(self, text: str, language: str = "auto") -> list[str]:
        """
        Detecta categorias de APIs com base em texto livre.

        Parâmetros
        ----------
        text : str
            Descrição do que o usuário quer coletar.
        language : str
            "pt", "en" ou "auto" (detecta automaticamente).

        Retorno
        -------
        list[str] : categorias detectadas.
        """
        categories: set[str] = set()
        text_lower = text.lower()

        # Remove pontuação e divide em palavras
        words = re.findall(r"[a-záàâãéèêíïóôõúüç]{3,}", text_lower)

        for word in words:
            if word in _KEYWORD_TO_CATEGORY:
                categories.update(_KEYWORD_TO_CATEGORY[word])

        return list(categories)

    def match_search_type(self, search_type: str) -> list[str]:
        """
        Mapeia o search_type do job para categorias.

        search_type pode ser: "flights", "news", "jobs", "leads",
        "weather", "finance", "ecommerce", etc.
        """
        # Match direto por categoria
        for cat_list in _KEYWORD_TO_CATEGORY.values():
            if search_type in cat_list:
                return [search_type]

        # Normaliza
        st = search_type.lower().strip()
        if st in _KEYWORD_TO_CATEGORY:
            return _KEYWORD_TO_CATEGORY[st]

        return [st] if st else []

    def score_relevance(self, api: dict, categories: list[str], url: str = "") -> float:
        """
        Calcula score de relevância de uma API para um conjunto de categorias.

        Parâmetros
        ----------
        api : dict
            Entrada do catálogo de APIs.
        categories : list[str]
            Categorias detectadas.
        url : str
            URL original (para match adicional).

        Retorno
        -------
        float : score 0.0–1.0
        """
        score = 0.0
        api_text = (
            f"{api.get('name', '')} {api.get('description', '')} {api.get('category', '')}"
        ).lower()

        for cat in categories:
            if cat.lower() in api_text:
                score += 0.4

        # Bônus: tier gratuito
        if api.get("free_tier"):
            score += 0.2

        # Bônus: sem key obrigatória
        if not api.get("key_required"):
            score += 0.1

        # Bônus: HTTPS
        if api.get("https"):
            score += 0.1

        return min(round(score, 3), 1.0)
