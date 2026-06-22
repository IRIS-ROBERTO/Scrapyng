"""
DuplicateDetector — detecta e remove duplicatas em datasets scraped.

Estratégias:
- Duplicata exata: hash MD5 do item serializado
- Duplicata fuzzy: similaridade de Jaccard entre conjuntos de tokens
  (útil para textos quase iguais, ex: descrições com leve variação)
"""

import hashlib
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detecta e remove duplicatas em datasets scraped.

    Exemplo de uso
    --------------
    detector = DuplicateDetector()

    # Detecção
    result = detector.detect(data)
    print(result["duplicate_rate"])  # 0.15 = 15% de duplicatas

    # Deduplicação
    clean_data = detector.deduplicate(data)

    # Fuzzy (textos similares)
    result = detector.detect(data, fuzzy=True, fuzzy_threshold=0.85)
    """

    def __init__(self, fuzzy_threshold: float = 0.85) -> None:
        """
        Parâmetros
        ----------
        fuzzy_threshold : float
            Limiar de similaridade Jaccard para considerar dois itens duplicatas fuzzy (0-1).
            Padrão: 0.85 (85% de similaridade).
        """
        self.fuzzy_threshold = fuzzy_threshold

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def detect(
        self,
        data: list[dict],
        fuzzy: bool = False,
        key_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Detecta duplicatas no dataset.

        Parâmetros
        ----------
        data : list[dict]
            Lista de itens a verificar.
        fuzzy : bool
            Se True, também detecta duplicatas fuzzy por similaridade de texto.
        key_fields : list[str], optional
            Se fornecido, usa apenas esses campos para comparação de identidade.
            Útil quando há campos de metadados (scraped_at, id) que diferem mas
            o conteúdo é o mesmo.

        Retorno
        -------
        dict com:
            duplicates_count : int
            unique_count : int
            duplicate_rate : float (0.0–1.0)
            duplicates : list[dict] (até 20 exemplos com index e duplicate_of)
            fuzzy_duplicates : list[dict] (se fuzzy=True)
        """
        if not data:
            return {
                "duplicates_count": 0,
                "unique_count": 0,
                "duplicate_rate": 0.0,
                "duplicates": [],
                "fuzzy_duplicates": [],
            }

        # Duplicatas exatas
        seen_hashes: dict[str, int] = {}
        duplicates: list[dict] = []
        unique_indices: list[int] = []

        for i, item in enumerate(data):
            h = self._hash_item(item, key_fields)
            if h in seen_hashes:
                duplicates.append({
                    "index": i,
                    "duplicate_of": seen_hashes[h],
                    "type": "exact",
                })
            else:
                seen_hashes[h] = i
                unique_indices.append(i)

        # Duplicatas fuzzy (opcional)
        fuzzy_duplicates: list[dict] = []
        if fuzzy and len(unique_indices) >= 2:
            fuzzy_duplicates = self._detect_fuzzy(data, unique_indices)

        total_dups = len(duplicates) + len(fuzzy_duplicates)
        dup_rate = total_dups / len(data)

        logger.debug(
            "DuplicateDetector.detect() | total=%d | exatas=%d | fuzzy=%d | rate=%.2f",
            len(data), len(duplicates), len(fuzzy_duplicates), dup_rate,
        )

        return {
            "duplicates_count": total_dups,
            "unique_count": len(unique_indices),
            "duplicate_rate": round(dup_rate, 4),
            "duplicates": duplicates[:20],
            "fuzzy_duplicates": fuzzy_duplicates[:20],
        }

    def deduplicate(
        self,
        data: list[dict],
        key_fields: list[str] | None = None,
        fuzzy: bool = False,
    ) -> list[dict]:
        """
        Remove duplicatas e retorna apenas itens únicos.

        Parâmetros
        ----------
        data : list[dict]
            Lista de itens.
        key_fields : list[str], optional
            Campos usados para determinar identidade.
        fuzzy : bool
            Se True, também remove duplicatas fuzzy.

        Retorno
        -------
        list[dict] com itens únicos (mantém a primeira ocorrência).
        """
        if not data:
            return []

        seen: set[str] = set()
        unique: list[dict] = []
        unique_indices: list[int] = []

        for i, item in enumerate(data):
            h = self._hash_item(item, key_fields)
            if h not in seen:
                seen.add(h)
                unique.append(item)
                unique_indices.append(i)

        if fuzzy and len(unique) >= 2:
            fuzzy_dups = self._detect_fuzzy(data, unique_indices)
            fuzzy_dup_indices = {d["index"] for d in fuzzy_dups}
            unique = [
                item for i, item in enumerate(unique)
                if unique_indices[i] not in fuzzy_dup_indices
            ]

        logger.debug(
            "DuplicateDetector.deduplicate() | original=%d | unique=%d",
            len(data), len(unique),
        )
        return unique

    def find_duplicates_by_field(
        self, data: list[dict], field: str
    ) -> dict[Any, list[int]]:
        """
        Agrupa itens por valor de um campo específico.
        Retorna apenas grupos com mais de 1 ocorrência.

        Útil para encontrar itens com mesmo ID, URL, título, etc.

        Retorno
        -------
        dict {valor: [indices_dos_itens]}
        """
        groups: dict[Any, list[int]] = {}
        for i, item in enumerate(data):
            val = item.get(field)
            if val is not None and val != "":
                key = str(val).strip().lower()
                groups.setdefault(key, []).append(i)

        return {k: v for k, v in groups.items() if len(v) > 1}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _hash_item(self, item: dict, key_fields: list[str] | None) -> str:
        """Gera hash MD5 do item para comparação exata."""
        if key_fields:
            subset = {k: item.get(k) for k in key_fields if k in item}
        else:
            subset = item

        # Normaliza: lowercase, strip, ordena chaves
        normalized = {
            k: str(v).strip().lower() if v is not None else ""
            for k, v in sorted(subset.items())
        }
        serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(serialized.encode()).hexdigest()

    def _detect_fuzzy(
        self, data: list[dict], unique_indices: list[int]
    ) -> list[dict]:
        """
        Detecta duplicatas fuzzy entre itens únicos usando similaridade de Jaccard.
        Compara a representação textual de cada item.
        """
        fuzzy_dups: list[dict] = []
        texts = [self._item_to_tokens(data[i]) for i in unique_indices]

        for i in range(len(unique_indices)):
            for j in range(i + 1, len(unique_indices)):
                sim = self._jaccard(texts[i], texts[j])
                if sim >= self.fuzzy_threshold:
                    fuzzy_dups.append({
                        "index": unique_indices[j],
                        "duplicate_of": unique_indices[i],
                        "type": "fuzzy",
                        "similarity": round(sim, 3),
                    })
                    # Evita comparar o item j com outros (já é duplicata)
                    break

        return fuzzy_dups

    @staticmethod
    def _item_to_tokens(item: dict) -> set[str]:
        """Converte item em conjunto de tokens para Jaccard."""
        text = " ".join(
            str(v) for v in item.values()
            if v is not None and isinstance(v, (str, int, float))
        ).lower()
        # Tokeniza por palavras com 3+ chars
        return set(re.findall(r"[a-záàâãéèêíïóôõúüç\d]{3,}", text))

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        """Calcula similaridade de Jaccard entre dois conjuntos."""
        if not a or not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union else 0.0
