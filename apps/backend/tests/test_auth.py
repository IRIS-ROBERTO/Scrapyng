from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient) -> None:
    # Register
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123",
            "full_name": "Test User",
        },
    )
    assert reg.status_code == 201, reg.text
    user_data = reg.json()
    assert user_data["email"] == "test@example.com"

    # Login
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    assert login.status_code == 200, login.text
    token_data = login.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Get /me
    token = token_data["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_duplicate_register(client: AsyncClient) -> None:
    payload = {
        "email": "dup@example.com",
        "username": "dupuser",
        "password": "password123",
    }
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/scrape/jobs")
    assert resp.status_code == 403
