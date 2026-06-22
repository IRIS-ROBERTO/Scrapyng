"""
VersionManager — versionamento de scrapers para suporte a auto-healing.

Persiste snapshots de configuração de scrapers (seletores, engine, settings)
em disco (JSON Lines) e SQLite opcional. Permite comparar versões, restaurar
configurações e detectar regressões automaticamente.
"""

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Diretório padrão de armazenamento de versões
_DEFAULT_STORAGE = Path(os.environ.get("SCRAPER_VERSIONS_DIR", "/tmp/scraper_versions"))


class VersionManager:
    """
    Armazena e gerencia versões de configuração de scrapers.

    Cada "versão" é um snapshot imutável de:
    - URL alvo
    - Seletores CSS/XPath
    - Engine usada (scrapy/playwright)
    - Settings customizados
    - Resultado de qualidade (score QA)

    Exemplo de uso
    --------------
    vm = VersionManager()

    # Salva configuração atual
    version_id = vm.save(
        scraper_id="meu_scraper",
        config={"url": "https://ex.com", "selectors": {"titulo": "h1::text"}, "engine": "scrapy"},
        quality_score=87.5,
    )

    # Restaura configuração de uma versão
    config = vm.restore(scraper_id="meu_scraper", version_id=version_id)

    # Lista versões disponíveis
    versions = vm.list_versions("meu_scraper")

    # Recupera a melhor versão por quality_score
    best = vm.get_best_version("meu_scraper")
    """

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else _DEFAULT_STORAGE
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.storage_dir / "versions.db"
        self._init_db()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def save(
        self,
        scraper_id: str,
        config: dict,
        quality_score: float = 0.0,
        notes: str = "",
    ) -> str:
        """
        Salva uma nova versão do scraper.

        Parâmetros
        ----------
        scraper_id : str
            Identificador único do scraper (ex: "google_news", "site_xyz").
        config : dict
            Configuração completa: url, selectors, engine, settings.
        quality_score : float
            Score QA (0-100) da execução que gerou esta versão.
        notes : str
            Notas opcionais sobre a versão.

        Retorno
        -------
        str : version_id gerado.
        """
        version_id = self._make_version_id(scraper_id, config)
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "version_id": version_id,
            "scraper_id": scraper_id,
            "created_at": now,
            "quality_score": quality_score,
            "notes": notes,
            "config": config,
        }

        # Salva em arquivo JSON Lines (audit trail imutável)
        jsonl_path = self.storage_dir / f"{scraper_id}.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Salva no SQLite para consultas rápidas
        self._db_insert(record)

        logger.info(
            "VersionManager.save() | scraper=%s | version=%s | score=%.1f",
            scraper_id, version_id, quality_score,
        )
        return version_id

    def restore(self, scraper_id: str, version_id: str) -> dict | None:
        """
        Recupera a configuração de uma versão específica.

        Retorno
        -------
        dict com a config, ou None se não encontrada.
        """
        row = self._db_fetch_by_version(scraper_id, version_id)
        if row:
            logger.info("VersionManager.restore() | scraper=%s | version=%s", scraper_id, version_id)
            return row["config"]
        logger.warning("VersionManager.restore() | versão não encontrada: %s/%s", scraper_id, version_id)
        return None

    def restore_latest(self, scraper_id: str) -> dict | None:
        """Recupera a config da versão mais recente de um scraper."""
        row = self._db_fetch_latest(scraper_id)
        return row["config"] if row else None

    def get_best_version(self, scraper_id: str) -> dict | None:
        """
        Retorna a configuração da versão com maior quality_score.
        """
        row = self._db_fetch_best(scraper_id)
        if row:
            return {"version_id": row["version_id"], "config": row["config"], "quality_score": row["quality_score"]}
        return None

    def list_versions(self, scraper_id: str, limit: int = 50) -> list[dict]:
        """
        Lista todas as versões de um scraper, mais recentes primeiro.

        Retorno
        -------
        list[dict] com version_id, created_at, quality_score, notes.
        """
        rows = self._db_list(scraper_id, limit)
        return [
            {
                "version_id": r["version_id"],
                "created_at": r["created_at"],
                "quality_score": r["quality_score"],
                "notes": r["notes"],
            }
            for r in rows
        ]

    def diff(self, scraper_id: str, version_a: str, version_b: str) -> dict:
        """
        Compara dois versões e retorna as diferenças de configuração.

        Retorno
        -------
        dict com:
            - added: campos/seletores adicionados em version_b
            - removed: campos/seletores removidos em version_b
            - changed: campos/seletores alterados
            - score_delta: diferença de quality_score
        """
        row_a = self._db_fetch_by_version(scraper_id, version_a)
        row_b = self._db_fetch_by_version(scraper_id, version_b)

        if not row_a or not row_b:
            return {"error": "Uma ou ambas as versões não foram encontradas."}

        cfg_a = row_a["config"]
        cfg_b = row_b["config"]
        sel_a = cfg_a.get("selectors", {})
        sel_b = cfg_b.get("selectors", {})

        added = {k: sel_b[k] for k in sel_b if k not in sel_a}
        removed = {k: sel_a[k] for k in sel_a if k not in sel_b}
        changed = {
            k: {"from": sel_a[k], "to": sel_b[k]}
            for k in sel_a
            if k in sel_b and sel_a[k] != sel_b[k]
        }

        return {
            "version_a": version_a,
            "version_b": version_b,
            "selectors": {"added": added, "removed": removed, "changed": changed},
            "engine_changed": cfg_a.get("engine") != cfg_b.get("engine"),
            "url_changed": cfg_a.get("url") != cfg_b.get("url"),
            "score_delta": row_b["quality_score"] - row_a["quality_score"],
        }

    def delete_old_versions(self, scraper_id: str, keep: int = 10) -> int:
        """
        Remove versões antigas, mantendo apenas as `keep` mais recentes.

        Retorno
        -------
        int : número de versões removidas.
        """
        all_versions = self.list_versions(scraper_id, limit=9999)
        to_delete = all_versions[keep:]
        for v in to_delete:
            self._db_delete(scraper_id, v["version_id"])
        logger.info(
            "VersionManager.delete_old_versions() | scraper=%s | removidas=%d",
            scraper_id, len(to_delete),
        )
        return len(to_delete)

    # ------------------------------------------------------------------
    # SQLite internals
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Cria a tabela se não existir."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scraper_versions (
                    version_id    TEXT NOT NULL,
                    scraper_id    TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    quality_score REAL NOT NULL DEFAULT 0,
                    notes         TEXT NOT NULL DEFAULT '',
                    config_json   TEXT NOT NULL,
                    PRIMARY KEY (scraper_id, version_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scraper_created ON scraper_versions(scraper_id, created_at)"
            )
            conn.commit()

    def _db_insert(self, record: dict) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scraper_versions
                    (version_id, scraper_id, created_at, quality_score, notes, config_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record["version_id"],
                    record["scraper_id"],
                    record["created_at"],
                    record["quality_score"],
                    record.get("notes", ""),
                    json.dumps(record["config"], ensure_ascii=False),
                ),
            )
            conn.commit()

    def _row_to_dict(self, row: tuple | None) -> dict | None:
        if not row:
            return None
        version_id, scraper_id, created_at, quality_score, notes, config_json = row
        return {
            "version_id": version_id,
            "scraper_id": scraper_id,
            "created_at": created_at,
            "quality_score": quality_score,
            "notes": notes,
            "config": json.loads(config_json),
        }

    def _db_fetch_by_version(self, scraper_id: str, version_id: str) -> dict | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scraper_versions WHERE scraper_id=? AND version_id=?",
                (scraper_id, version_id),
            ).fetchone()
        return self._row_to_dict(row)

    def _db_fetch_latest(self, scraper_id: str) -> dict | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scraper_versions WHERE scraper_id=? ORDER BY created_at DESC LIMIT 1",
                (scraper_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def _db_fetch_best(self, scraper_id: str) -> dict | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scraper_versions WHERE scraper_id=? ORDER BY quality_score DESC LIMIT 1",
                (scraper_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def _db_list(self, scraper_id: str, limit: int) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scraper_versions WHERE scraper_id=? ORDER BY created_at DESC LIMIT ?",
                (scraper_id, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]  # type: ignore[misc]

    def _db_delete(self, scraper_id: str, version_id: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "DELETE FROM scraper_versions WHERE scraper_id=? AND version_id=?",
                (scraper_id, version_id),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_version_id(scraper_id: str, config: dict) -> str:
        """Gera version_id único baseado no scraper_id + config + timestamp."""
        ts = datetime.now(timezone.utc).isoformat()
        content = f"{scraper_id}:{ts}:{json.dumps(config, sort_keys=True)}"
        return "v_" + hashlib.sha1(content.encode()).hexdigest()[:12]
