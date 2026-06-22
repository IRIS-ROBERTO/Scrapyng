"""
API Discovery Engine — identifica e recomenda APIs públicas como alternativas ao scraping.

Exporta as classes principais.
"""

from .public_api_indexer import PublicAPIIndexer
from .api_matcher import APIMatcher
from .api_recommender import APIRecommender

__all__ = [
    "PublicAPIIndexer",
    "APIMatcher",
    "APIRecommender",
]
