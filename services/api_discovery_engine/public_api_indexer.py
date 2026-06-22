"""
PublicAPIIndexer — indexa o catálogo público de APIs do repositório public-apis/public-apis.

Parseia o README.md (formato Markdown com tabelas) e mantém índice em memória
e em SQLite para pesquisa rápida por categoria, nome e palavras-chave.

Fonte: https://raw.githubusercontent.com/public-apis/public-apis/master/README.md
"""

import hashlib
import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_README_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
_DEFAULT_DB = "/tmp/public_apis_index.db"

# Regex para linhas de tabela Markdown: | Name | Description | Auth | HTTPS | CORS | Link |
_TABLE_ROW = re.compile(
    r"\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|"   # [Name](url)
    r"([^|]*)\|"                              # Description
    r"([^|]*)\|"                              # Auth
    r"([^|]*)\|"                              # HTTPS
    r"([^|]*)\|"                              # CORS
)

# Regex para detectar cabeçalho de categoria: ## Category Name
_CATEGORY_HEADER = re.compile(r"^#{1,3}\s+(.+)$")


class PublicAPIIndexer:
    """
    Baixa e indexa o catálogo de APIs públicas do repositório public-apis.

    Exemplo de uso
    --------------
    indexer = PublicAPIIndexer()
    await indexer.fetch_and_index()
    results = indexer.search("weather")
    """

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self.db_path = db_path
        self._init_db()
        self._last_fetched: datetime | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def fetch_and_index(self, force: bool = False) -> int:
        """
        Baixa o README do public-apis e indexa todas as APIs encontradas.

        Parâmetros
        ----------
        force : bool
            Se True, atualiza mesmo que tenha sido indexado hoje.

        Retorno
        -------
        int : número de APIs indexadas.
        """
        # Verifica se já indexou hoje
        if not force and self._was_indexed_today():
            count = self._count_indexed()
            logger.info("PublicAPIIndexer: índice atual com %d APIs. Use force=True para atualizar.", count)
            return count

        logger.info("PublicAPIIndexer: baixando catálogo de %s", _README_URL)
        readme = await self._fetch_readme()
        if not readme:
            logger.error("PublicAPIIndexer: falha ao baixar README.")
            return 0

        apis = self._parse_readme(readme)
        count = self._save_to_db(apis)
        self._last_fetched = datetime.now(timezone.utc)
        logger.info("PublicAPIIndexer: %d APIs indexadas.", count)
        return count

    def search(
        self,
        query: str,
        category: str | None = None,
        free_only: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """
        Busca APIs por palavras-chave, categoria e filtros.

        Parâmetros
        ----------
        query : str
            Palavras-chave para buscar no nome e descrição.
        category : str, optional
            Filtra por categoria (case-insensitive).
        free_only : bool
            Se True, retorna apenas APIs sem autenticação obrigatória.
        limit : int
            Máximo de resultados.

        Retorno
        -------
        list[dict] com campos: name, url, description, category, auth, https, cors.
        """
        conditions = []
        params: list = []

        if query:
            conditions.append("(name LIKE ? OR description LIKE ? OR category LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])

        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")

        if free_only:
            conditions.append("auth IN ('', 'No', 'no', 'None', 'none')")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM public_apis {where} ORDER BY name LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        return [dict(r) for r in rows]

    def list_categories(self) -> list[str]:
        """Retorna todas as categorias indexadas."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM public_apis ORDER BY category"
            ).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_by_category(self, category: str, limit: int = 50) -> list[dict]:
        """Retorna todas as APIs de uma categoria."""
        return self.search("", category=category, limit=limit)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _fetch_readme(self) -> str:
        """Baixa o README.md do repositório public-apis."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(_README_URL)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            logger.error("PublicAPIIndexer._fetch_readme(): %s", exc)
            return ""

    def _parse_readme(self, readme: str) -> list[dict]:
        """Parseia o README e extrai entradas de APIs."""
        apis: list[dict] = []
        current_category = "Uncategorized"

        for line in readme.splitlines():
            # Detecta categoria
            cat_match = _CATEGORY_HEADER.match(line.strip())
            if cat_match:
                # Remove âncoras Markdown [text](#id)
                cat = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cat_match.group(1)).strip()
                # Ignora cabeçalhos de nível muito alto (# APIs, ## Index)
                if len(cat) > 2 and not re.match(r"^(api|apis|index|table)", cat.lower()):
                    current_category = cat
                continue

            # Detecta linha de tabela
            row_match = _TABLE_ROW.search(line)
            if row_match:
                name = row_match.group(1).strip()
                url = row_match.group(2).strip()
                description = row_match.group(3).strip()
                auth = row_match.group(4).strip()
                https_supported = row_match.group(5).strip().lower() in ("yes", "true", "✓")
                cors = row_match.group(6).strip()

                if name and url and name.lower() not in ("name", "api"):
                    apis.append({
                        "id": hashlib.sha1(f"{name}:{url}".encode()).hexdigest()[:12],
                        "name": name,
                        "url": url,
                        "description": description,
                        "category": current_category,
                        "auth": auth,
                        "https": https_supported,
                        "cors": cors,
                        "free_tier": auth.lower() in ("", "no", "none", "apikey"),
                        "key_required": bool(auth) and auth.lower() not in ("no", "none", ""),
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    })

        logger.debug("PublicAPIIndexer._parse_readme(): %d entradas encontradas", len(apis))
        return apis

    def _save_to_db(self, apis: list[dict]) -> int:
        """Salva/atualiza APIs no banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM public_apis")
            for api in apis:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO public_apis
                        (id, name, url, description, category, auth, https, cors, free_tier, key_required, indexed_at)
                    VALUES
                        (:id, :name, :url, :description, :category, :auth, :https, :cors, :free_tier, :key_required, :indexed_at)
                    """,
                    {**api, "https": int(api["https"]), "free_tier": int(api["free_tier"]), "key_required": int(api["key_required"])},
                )
            conn.commit()
        return len(apis)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS public_apis (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    category    TEXT NOT NULL DEFAULT '',
                    auth        TEXT NOT NULL DEFAULT '',
                    https       INTEGER NOT NULL DEFAULT 1,
                    cors        TEXT NOT NULL DEFAULT '',
                    free_tier   INTEGER NOT NULL DEFAULT 1,
                    key_required INTEGER NOT NULL DEFAULT 0,
                    indexed_at  TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_apis_category ON public_apis(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_apis_name ON public_apis(name)"
            )
            conn.commit()

    def _count_indexed(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM public_apis").fetchone()[0]

    def _was_indexed_today(self) -> bool:
        count = self._count_indexed()
        if count == 0:
            return False
        # Verifica data da última indexação
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT indexed_at FROM public_apis ORDER BY indexed_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return False
        try:
            indexed_at = datetime.fromisoformat(row[0])
            now = datetime.now(timezone.utc)
            return (now - indexed_at).total_seconds() < 86400  # 24h
        except Exception:
            return False
