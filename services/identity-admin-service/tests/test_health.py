"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient) -> None:
    """Test basic health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "identity-admin-service"
    assert "version" in data


@pytest.mark.anyio
async def test_readiness_check(client: AsyncClient) -> None:
    """Test readiness check endpoint."""
    response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_liveness_check(client: AsyncClient) -> None:
    """Test liveness check endpoint."""
    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
