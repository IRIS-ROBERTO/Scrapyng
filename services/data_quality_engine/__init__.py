"""
Data Quality Engine — avaliação e garantia de qualidade dos dados scraped.

Dimensões de avaliação:
- Completude (campos preenchidos)       → 30 pts
- Consistência de tipos                 → 20 pts
- Unicidade (sem duplicatas)            → 20 pts
- Validade (valores não-vazios)         → 20 pts
- Formato (emails, URLs, datas válidos) → 10 pts

Score total: 0-100 com grade A/B/C/D/F.
"""

from .quality_score import QualityScorer
from .duplicate_detector import DuplicateDetector
from .schema_validator import SchemaValidator
from .change_detector import ChangeDetector

__all__ = [
    "QualityScorer",
    "DuplicateDetector",
    "SchemaValidator",
    "ChangeDetector",
]
