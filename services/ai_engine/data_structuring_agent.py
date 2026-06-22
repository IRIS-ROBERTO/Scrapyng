"""
Data structuring agent.

Transforms raw, messy data extracted by scrapers into clean, normalized,
deduplicated JSON using NVIDIA NIM.
"""

from __future__ import annotations

import hashlib
import json
import re
import structlog
from typing import Any

from .nvidia_client import NvidiaClient
from .prompts.data_structuring import STRUCTURING_SYSTEM_PROMPT, build_structuring_prompt

log = structlog.get_logger(__name__)

# Maximum items sent to the AI in a single batch
_AI_BATCH_SIZE = 50


class DataStructuringAgent:
    """
    Cleans, normalizes, and deduplicates raw scraped data.

    For large datasets (> 50 items) the agent processes in batches and
    merges the results, performing a final deduplication pass.

    Example
    -------
    ::

        agent = DataStructuringAgent(nvidia_client)
        result = await agent.structure(
            raw_data=[{"price": "R$ 1.299,90", "date": "22/06/2026"}, ...],
            context="Produtos de eletrônicos do Mercado Livre",
        )
        print(result["structured_data"])   # normalized list
        print(result["quality_score"])     # 0-100
    """

    def __init__(self, client: NvidiaClient) -> None:
        self._client = client

    async def structure(self, raw_data: list[dict], context: str) -> dict:
        """
        Structure and normalize raw scraping data.

        Parameters
        ----------
        raw_data:
            List of raw dicts as extracted by the spider.
        context:
            Description of what was scraped (used in the AI prompt for context).

        Returns
        -------
        dict
            - ``structured_data``: list of clean, normalized objects
            - ``schema``: inferred JSON schema for the dataset
            - ``stats``: input_count, output_count, duplicates_removed, fields_normalized
            - ``quality_notes``: list of warnings
            - ``quality_score``: 0-100
        """
        log.info("structuring_agent_start", items=len(raw_data), context=context)

        if not raw_data:
            return self._empty_result(context)

        # Pre-processing: remove trivially empty records
        filtered = self._remove_empty_records(raw_data)
        removed_empty = len(raw_data) - len(filtered)

        if len(filtered) <= _AI_BATCH_SIZE:
            result = await self._process_batch(filtered, context)
        else:
            result = await self._process_large_dataset(filtered, context)

        # Record pre-AI deduplication in stats
        result.setdefault("stats", {})
        result["stats"]["empty_removed"] = removed_empty
        result["stats"]["input_count"] = len(raw_data)

        log.info(
            "structuring_agent_done",
            input=len(raw_data),
            output=len(result.get("structured_data", [])),
            score=result.get("quality_score"),
        )
        return result

    async def normalize_field(
        self,
        field_name: str,
        values: list[Any],
        field_type: str = "auto",
    ) -> list[Any]:
        """
        Normalize a single field across multiple values.

        Useful when you know exactly which field needs cleaning without
        running the full structuring pipeline.

        Parameters
        ----------
        field_name:
            Name of the field (for context).
        values:
            Raw values to normalize.
        field_type:
            One of: auto | price | date | phone | url | text | number

        Returns
        -------
        list
            Normalized values in the same order as input.
        """
        prompt = (
            f"Normalize estes valores do campo '{field_name}' (tipo: {field_type}).\n\n"
            f"Valores brutos:\n{json.dumps(values[:100], ensure_ascii=False)}\n\n"
            f"Retorne JSON: {{ \"normalized\": [lista de valores normalizados na mesma ordem] }}"
        )
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=STRUCTURING_SYSTEM_PROMPT,
            max_tokens=1500,
        )
        return result.get("normalized", values)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _process_batch(self, data: list[dict], context: str) -> dict:
        """Send a single batch (≤50 items) to the AI."""
        user_message = build_structuring_prompt(raw_data=data, context=context)
        result = await self._client.chat_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=STRUCTURING_SYSTEM_PROMPT,
            max_tokens=6000,
        )
        return result

    async def _process_large_dataset(self, data: list[dict], context: str) -> dict:
        """Process datasets > 50 items in batches and merge results."""
        import asyncio

        batches = [
            data[i: i + _AI_BATCH_SIZE]
            for i in range(0, len(data), _AI_BATCH_SIZE)
        ]
        log.info("structuring_agent_batching", batches=len(batches), total_items=len(data))

        # Process batches sequentially to avoid overwhelming the API
        all_structured: list[dict] = []
        all_notes: list[str] = []
        schema: dict = {}
        scores: list[float] = []
        fields_normalized: set[str] = set()

        for idx, batch in enumerate(batches):
            log.info("structuring_agent_batch", batch_num=idx + 1, total=len(batches))
            result = await self._process_batch(batch, context)
            all_structured.extend(result.get("structured_data", []))
            all_notes.extend(result.get("quality_notes", []))
            if result.get("schema") and not schema:
                schema = result["schema"]
            if result.get("quality_score") is not None:
                scores.append(float(result["quality_score"]))
            for f in result.get("stats", {}).get("fields_normalized", []):
                fields_normalized.add(f)

        # Deduplicate merged results
        deduped, dupes = self._deduplicate(all_structured)

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        return {
            "structured_data": deduped,
            "schema": schema,
            "stats": {
                "input_count": len(data),
                "output_count": len(deduped),
                "duplicates_removed": dupes,
                "fields_normalized": sorted(fields_normalized),
            },
            "quality_notes": list(dict.fromkeys(all_notes)),  # dedupe notes
            "quality_score": avg_score,
        }

    @staticmethod
    def _remove_empty_records(data: list[dict]) -> list[dict]:
        """Remove records where all values are None, empty string, or empty list."""
        result = []
        for record in data:
            values = [v for v in record.values() if v is not None and v != "" and v != []]
            if values:
                result.append(record)
        return result

    @staticmethod
    def _deduplicate(data: list[dict]) -> tuple[list[dict], int]:
        """
        Remove duplicate records using a stable hash of their JSON representation.

        Returns (deduplicated_list, number_removed).
        """
        seen: set[str] = set()
        unique: list[dict] = []
        for record in data:
            try:
                key = hashlib.md5(
                    json.dumps(record, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
            except (TypeError, ValueError):
                key = str(record)
            if key not in seen:
                seen.add(key)
                unique.append(record)
        removed = len(data) - len(unique)
        return unique, removed

    @staticmethod
    def _empty_result(context: str) -> dict:
        return {
            "structured_data": [],
            "schema": {"fields": []},
            "stats": {
                "input_count": 0,
                "output_count": 0,
                "duplicates_removed": 0,
                "fields_normalized": [],
                "empty_removed": 0,
            },
            "quality_notes": ["Input data was empty."],
            "quality_score": 0,
        }
