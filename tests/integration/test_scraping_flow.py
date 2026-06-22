"""
Testes de integração do fluxo de scraping.
Requer serviços rodando (PostgreSQL, Redis).
"""
import pytest
import httpx
import asyncio


BASE_URL = "http://localhost:8000/api/v1"


@pytest.fixture
async def auth_token():
    """Obtém token JWT para os testes."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "test@test.com",
            "password": "testpassword123"
        })
        if resp.status_code == 200:
            return resp.json()["access_token"]
        # Registrar e tentar de novo
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": "test@test.com",
            "password": "testpassword123",
            "name": "Test User"
        })
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "test@test.com",
            "password": "testpassword123"
        })
        return resp.json()["access_token"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_endpoint():
    """GET /health deve retornar status 200."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "services" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_instant_scrape_public_site(auth_token):
    """Scraping instantâneo de site público deve retornar dados."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BASE_URL}/scrape/instant",
            json={
                "url": "https://books.toscrape.com/",
                "selectors": {
                    "title": "article.product_pod h3 a",
                    "price": "article.product_pod .price_color"
                },
                "use_playwright": False
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert resp.status_code in (200, 202)
        if resp.status_code == 200:
            data = resp.json()
            assert "job_id" in data or "results" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_jobs_requires_auth():
    """GET /scrape/jobs deve exigir autenticação."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/scrape/jobs")
        assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_jobs_with_auth(auth_token):
    """GET /scrape/jobs deve retornar lista para usuário autenticado."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/scrape/jobs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
