"""
ResultNormalizer — normaliza dados brutos de scraping para formato padrão.

Formato de saída padrão:
{
    "items": [
        {
            "id": "<hash único>",
            "source_url": str,
            "scraped_at": ISO8601,
            "fields": {campo: valor_normalizado, ...},
            "raw": {campo: valor_bruto, ...},
        }
    ],
    "meta": {
        "total": int,
        "source_url": str,
        "scraped_at": str,
        "engine": str,
        "version": "1.0",
    }
}
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResultNormalizer:
    """
    Normaliza e enriquece dados brutos vindos do ScrapyRunner ou PlaywrightRunner.

    Operações realizadas:
    - Limpeza de whitespace excessivo
    - Normalização de URLs (absolutas)
    - Detecção e parsing de datas ISO8601
    - Detecção e normalização de preços/valores numéricos
    - Geração de ID único por item (hash SHA-1)
    - Adição de metadados (scraped_at, source_url, engine)
    """

    VERSION = "1.0"

    # Padrões de reconhecimento de tipos
    _RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    _RE_URL = re.compile(r"https?://[^\s\"'<>]+")
    _RE_PRICE = re.compile(r"R?\$?\s*[\d.,]+")
    _RE_DATE_ISO = re.compile(
        r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?"
    )
    _RE_DATE_BR = re.compile(r"\d{2}/\d{2}/\d{4}")

    def __init__(self, source_url: str = "", engine: str = "unknown") -> None:
        self.source_url = source_url
        self.engine = engine

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def normalize(
        self,
        raw_data: list[dict] | dict,
        source_url: str = "",
        engine: str = "",
    ) -> dict:
        """
        Normaliza uma lista de itens brutos ou um dict único.

        Parâmetros
        ----------
        raw_data : list[dict] | dict
            Dados brutos vindos do scraping.
        source_url : str
            URL de origem (sobrescreve o valor do construtor).
        engine : str
            Motor usado ("scrapy", "playwright", etc.).

        Retorno
        -------
        dict no formato padrão com "items" e "meta".
        """
        src = source_url or self.source_url
        eng = engine or self.engine
        now = datetime.now(timezone.utc).isoformat()

        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        items: list[dict] = []
        for raw_item in raw_data:
            normalized = self._normalize_item(raw_item, src, now)
            items.append(normalized)

        result = {
            "items": items,
            "meta": {
                "total": len(items),
                "source_url": src,
                "scraped_at": now,
                "engine": eng,
                "version": self.VERSION,
            },
        }
        logger.info(
            "ResultNormalizer.normalize() | engine=%s | itens=%d | url=%s",
            eng, len(items), src,
        )
        return result

    def normalize_item(self, raw_item: dict, source_url: str = "") -> dict:
        """Normaliza um único item (atalho para normalize() com um item)."""
        result = self.normalize([raw_item], source_url=source_url)
        return result["items"][0] if result["items"] else {}

    def flatten(self, normalized: dict) -> list[dict]:
        """
        Achata o formato padrão para lista plana de dicts (campos + meta inline).
        Útil para exportação CSV.
        """
        meta = normalized.get("meta", {})
        flat: list[dict] = []
        for item in normalized.get("items", []):
            row = {**item.get("fields", {})}
            row["_id"] = item.get("id", "")
            row["_source_url"] = item.get("source_url", meta.get("source_url", ""))
            row["_scraped_at"] = item.get("scraped_at", meta.get("scraped_at", ""))
            flat.append(row)
        return flat

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _normalize_item(self, raw: dict, source_url: str, scraped_at: str) -> dict:
        """Processa um item bruto e retorna o item normalizado."""
        fields: dict = {}

        for key, value in raw.items():
            if key in ("url", "status", "title", "error", "screenshot_b64"):
                # Campos de metadados — mantém sem transformar em "fields"
                continue
            fields[key] = self._normalize_value(key, value, source_url)

        # Metadados de scraping presentes no item
        item_url = raw.get("url", source_url)
        item_title = raw.get("title", "")

        item = {
            "id": self._make_id(fields, item_url),
            "source_url": item_url,
            "scraped_at": scraped_at,
            "title": item_title,
            "fields": fields,
            "raw": raw,
        }
        return item

    def _normalize_value(self, key: str, value: Any, base_url: str) -> Any:
        """Normaliza um valor baseado em seu conteúdo e nome do campo."""
        if value is None:
            return None

        # Lista: normaliza cada elemento
        if isinstance(value, list):
            normalized = [self._normalize_scalar(key, v, base_url) for v in value]
            # Se só tem 1 item, desempacota
            return normalized[0] if len(normalized) == 1 else normalized

        return self._normalize_scalar(key, value, base_url)

    def _normalize_scalar(self, key: str, value: Any, base_url: str) -> Any:
        """Normaliza um valor escalar."""
        if not isinstance(value, str):
            return value

        value = self._clean_text(value)

        if not value:
            return None

        # Tenta inferir tipo pelo nome do campo
        key_lower = key.lower()

        if any(k in key_lower for k in ("url", "href", "link", "src", "image")):
            return self._normalize_url(value, base_url)

        if any(k in key_lower for k in ("email", "mail", "e-mail")):
            return self._extract_email(value)

        if any(k in key_lower for k in ("price", "preco", "valor", "custo", "cost")):
            return self._normalize_price(value)

        if any(k in key_lower for k in ("date", "data", "datetime", "published", "created")):
            return self._normalize_date(value)

        # Tenta inferir pelo conteúdo
        if self._RE_DATE_ISO.fullmatch(value):
            return self._normalize_date(value)

        return value

    # ------------------------------------------------------------------
    # Normalização por tipo
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove espaços extras, tabs e newlines desnecessários."""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _normalize_url(self, value: str, base_url: str) -> str:
        """Converte URLs relativas em absolutas."""
        if not value:
            return value
        if value.startswith(("http://", "https://", "//", "data:")):
            return value
        if value.startswith("/") and base_url:
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{value}"
        return value

    def _extract_email(self, value: str) -> str | None:
        """Extrai o primeiro email encontrado no texto."""
        match = self._RE_EMAIL.search(value)
        return match.group(0) if match else value

    def _normalize_price(self, value: str) -> float | str:
        """
        Converte strings de preço em float.
        Ex: "R$ 1.299,90" → 1299.9; "$ 1,299.90" → 1299.9
        """
        # Remove símbolos de moeda e espaços
        cleaned = re.sub(r"[R$€£¥\s]", "", value)
        # Detecta formato BR (1.000,00) vs US (1,000.00)
        if re.search(r"\d\.\d{3},\d{2}$", cleaned):
            # Formato BR
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Formato US ou sem separador de milhar
            cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return value

    def _normalize_date(self, value: str) -> str:
        """
        Tenta converter data para ISO8601.
        Suporta: ISO8601, DD/MM/YYYY (BR), YYYY-MM-DD.
        """
        # Já é ISO8601
        if self._RE_DATE_ISO.fullmatch(value):
            return value

        # Formato BR: DD/MM/YYYY
        match = self._RE_DATE_BR.search(value)
        if match:
            try:
                d, m, y = match.group(0).split("/")
                return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
            except Exception:
                pass

        return value

    @staticmethod
    def _make_id(fields: dict, url: str) -> str:
        """Gera ID único SHA-1 baseado nos campos e URL."""
        content = json.dumps(
            {"fields": {k: str(v) for k, v in sorted(fields.items())}, "url": url},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha1(content.encode()).hexdigest()[:16]
