"""
Integration tests for Audit Service API endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from audit_service.domain.entities.audit_event import AuditAction, AuditSeverity
from audit_service.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audit-service"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient) -> None:
        """Test readiness endpoint returns ready status."""
        response = await client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert "checks" in data


class TestAuditEndpoints:
    """Tests for audit event API endpoints."""

    @pytest.mark.asyncio
    async def test_create_audit_event(self, client: AsyncClient) -> None:
        """Test creating an audit event via API."""
        payload = {
            "service_name": "test-service",
            "actor_id": "user-123",
            "actor_type": "user",
            "action": AuditAction.CREATE.value,
            "severity": AuditSeverity.INFO.value,
            "resource_type": "document",
            "resource_id": "doc-456",
            "description": "Test event",
        }

        response = await client.post("/api/v1/audit/events", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["actor_id"] == "user-123"
        assert data["action"] == "CREATE"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_audit_events(self, client: AsyncClient) -> None:
        """Test listing audit events via API."""
        response = await client.get("/api/v1/audit/events")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_audit_events_with_pagination(
        self, client: AsyncClient
    ) -> None:
        """Test listing audit events with pagination parameters."""
        response = await client.get(
            "/api/v1/audit/events",
            params={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
