"""Exporta dados para JSON com indentação e metadados."""
import json
import io
from datetime import datetime
from typing import Any


class JSONExporter:
    def export(self, data: list[dict], filename: str | None = None, include_meta: bool = True) -> str:
        content = self.export_string(data, include_meta=include_meta)
        path = filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def export_string(self, data: list[dict], include_meta: bool = True) -> str:
        payload: dict[str, Any] = {"data": data}
        if include_meta:
            payload["meta"] = {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "count": len(data),
                "source": "WebScrapy AI Platform",
                "version": "1.0",
            }
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    def export_bytes(self, data: list[dict], include_meta: bool = True) -> bytes:
        return self.export_string(data, include_meta=include_meta).encode("utf-8")
