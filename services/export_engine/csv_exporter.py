"""Exporta dados para CSV usando pandas."""
import io
import csv
import pandas as pd
from pathlib import Path
from typing import Any


class CSVExporter:
    def export(self, data: list[dict], filename: str | None = None) -> str:
        """Salva em arquivo e retorna o caminho."""
        df = self._to_dataframe(data)
        path = filename or "export.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def export_bytes(self, data: list[dict]) -> bytes:
        """Retorna CSV como bytes (para streaming HTTP)."""
        df = self._to_dataframe(data)
        buf = io.BytesIO()
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        return buf.getvalue()

    def export_string(self, data: list[dict]) -> str:
        """Retorna CSV como string."""
        return self.export_bytes(data).decode("utf-8-sig")

    def _to_dataframe(self, data: list[dict]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        # Achatar listas e dicts dentro dos campos
        flat_data = []
        for item in data:
            flat = {}
            for k, v in item.items():
                if isinstance(v, (list, dict)):
                    flat[k] = str(v)
                else:
                    flat[k] = v
            flat_data.append(flat)
        return pd.DataFrame(flat_data)
