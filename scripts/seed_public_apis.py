"""
Script para indexar APIs públicas do repositório public-apis no banco de dados.
Executa parse do README.md e popula a tabela public_api_catalog.
"""
import re
import asyncio
import asyncpg
import os
from pathlib import Path


README_PATH = Path(__file__).parent.parent.parent / "external_repos" / "public-apis" / "README.md"


def parse_public_apis_readme(readme_path: Path) -> list[dict]:
    """
    Parseia o README do public-apis e retorna lista de APIs.
    Formato das linhas: | API | Description | Auth | HTTPS | CORS | Link |
    """
    apis = []
    current_category = "General"

    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    # Encontrar seções e suas tabelas
    section_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    table_row_pattern = re.compile(
        r"^\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|",
        re.MULTILINE
    )

    lines = content.split("\n")
    for line in lines:
        section_match = re.match(r"^## (.+)$", line)
        if section_match:
            current_category = section_match.group(1).strip()
            continue

        table_match = re.match(
            r"^\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|",
            line
        )
        if table_match:
            name = table_match.group(1).strip()
            url = table_match.group(2).strip()
            description = table_match.group(3).strip()
            auth = table_match.group(4).strip()
            https = table_match.group(5).strip().lower() == "yes"
            cors = table_match.group(6).strip().lower() == "yes"

            if name and url and not name.startswith("API"):
                # Mapear categoria para search_types
                search_types = []
                cat_lower = current_category.lower()
                if any(k in cat_lower for k in ["news", "media"]):
                    search_types.append("news")
                if any(k in cat_lower for k in ["transport", "aviation", "flight"]):
                    search_types.append("flights")
                if any(k in cat_lower for k in ["job", "career", "employment"]):
                    search_types.append("jobs")
                if any(k in cat_lower for k in ["business", "finance", "email"]):
                    search_types.append("leads")

                apis.append({
                    "name": name,
                    "description": description,
                    "url": url,
                    "category": current_category,
                    "auth_required": auth not in ("No", "", "null"),
                    "auth_type": auth if auth != "No" else "No",
                    "https_only": https,
                    "cors_supported": cors,
                    "search_types": search_types,
                })

    return apis


async def seed_to_database(apis: list[dict]) -> None:
    db_url = os.environ.get("DATABASE_URL", "postgresql://webscrapy:webscrapy123@localhost:5432/webscrapy")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        # Limpar tabela antes de popular
        await conn.execute("DELETE FROM public_api_catalog WHERE name NOT IN (SELECT name FROM public_api_catalog WHERE name IN ('NewsAPI', 'GNews', 'Aviationstack', 'Amadeus', 'Arbeitnow', 'Hunter.io'))")

        inserted = 0
        for api in apis:
            await conn.execute("""
                INSERT INTO public_api_catalog (name, description, url, category, auth_required, auth_type, https_only, cors_supported, search_types)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT DO NOTHING
            """, api["name"], api["description"], api["url"], api["category"],
                api["auth_required"], api["auth_type"], api["https_only"], api["cors_supported"],
                api["search_types"])
            inserted += 1

        print(f"✓ {inserted} APIs indexadas no banco de dados")
    finally:
        await conn.close()


if __name__ == "__main__":
    print(f"Lendo README: {README_PATH}")
    if not README_PATH.exists():
        print("⚠ README do public-apis não encontrado. Certifique-se de clonar external_repos/public-apis primeiro.")
        exit(1)

    apis = parse_public_apis_readme(README_PATH)
    print(f"→ {len(apis)} APIs encontradas no catálogo")

    asyncio.run(seed_to_database(apis))
