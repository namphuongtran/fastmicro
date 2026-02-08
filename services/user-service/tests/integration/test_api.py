"""Integration tests for user-service API endpoints.

Uses TestClient with dependency overrides to test the full HTTP layer
without requiring a real database.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from shared.application.base_service import ServiceContext

from user_service.api import dependencies as deps
from user_service.domain.entities.user import User
from user_service.main import create_app


# ---- fixtures ----

@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.exists_by_email = AsyncMock(return_value=False)
    repo.add = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_by_tenant = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def app(mock_repo: AsyncMock):
    """Build test app with overridden dependencies."""
    application = create_app()

    # Wire the mock repository into the singleton
    deps.set_repository(mock_repo)
    deps.set_event_dispatcher(AsyncMock())

    # Override service context to return a simple context
    async def _override_ctx() -> ServiceContext:
        return ServiceContext(
            user_id="test-user",
            tenant_id="test-tenant",
        )

    application.dependency_overrides[deps.get_service_context] = _override_ctx

    yield application

    # Cleanup
    application.dependency_overrides.clear()
    deps._user_repository = None
    deps._event_dispatcher = None


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_user() -> User:
    return User.create(
        id="u-100",
        email="api@example.com",
        display_name="API User",
        tenant_id="test-tenant",
    )


# ---- POST /api/v1/users ----

class TestCreateUserEndpoint:
    """Tests for POST /api/v1/users."""

    def test_create_user_201(self, client: TestClient, mock_repo: AsyncMock):
        resp = client.post(
            "/api/v1/users",
            json={
                "email": "new@example.com",
                "display_name": "New User",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["display_name"] == "New User"
        assert data["is_active"] is True

    def test_create_user_409_duplicate_email(
        self, client: TestClient, mock_repo: AsyncMock
    ):
        mock_repo.exists_by_email.return_value = True
        resp = client.post(
            "/api/v1/users",
            json={"email": "dup@example.com", "display_name": "Dup"},
        )
        assert resp.status_code == 409

    def test_create_user_422_missing_email(self, client: TestClient):
        resp = client.post("/api/v1/users", json={"display_name": "No Email"})
        assert resp.status_code == 422


# ---- GET /api/v1/users/{user_id} ----

class TestGetUserEndpoint:
    """Tests for GET /api/v1/users/{user_id}."""

    def test_get_user_200(
        self, client: TestClient, mock_repo: AsyncMock, sample_user: User
    ):
        mock_repo.get_by_id.return_value = sample_user
        resp = client.get("/api/v1/users/u-100")
        assert resp.status_code == 200
        assert resp.json()["id"] == "u-100"

    def test_get_user_404(self, client: TestClient, mock_repo: AsyncMock):
        mock_repo.get_by_id.return_value = None
        resp = client.get("/api/v1/users/nonexistent")
        assert resp.status_code == 404


# ---- PATCH /api/v1/users/{user_id} ----

class TestUpdateUserEndpoint:
    """Tests for PATCH /api/v1/users/{user_id}."""

    def test_update_user_200(
        self, client: TestClient, mock_repo: AsyncMock, sample_user: User
    ):
        mock_repo.get_by_id.return_value = sample_user
        resp = client.patch(
            "/api/v1/users/u-100",
            json={"display_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    def test_update_user_404(self, client: TestClient, mock_repo: AsyncMock):
        mock_repo.get_by_id.return_value = None
        resp = client.patch(
            "/api/v1/users/missing",
            json={"display_name": "X"},
        )
        assert resp.status_code == 404


# ---- POST /api/v1/users/{user_id}/deactivate ----

class TestDeactivateUserEndpoint:
    """Tests for POST /api/v1/users/{user_id}/deactivate."""

    def test_deactivate_user_200(
        self, client: TestClient, mock_repo: AsyncMock, sample_user: User
    ):
        mock_repo.get_by_id.return_value = sample_user
        resp = client.post("/api/v1/users/u-100/deactivate")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


# ---- DELETE /api/v1/users/{user_id} ----

class TestDeleteUserEndpoint:
    """Tests for DELETE /api/v1/users/{user_id}."""

    def test_delete_user_204(
        self, client: TestClient, mock_repo: AsyncMock, sample_user: User
    ):
        mock_repo.get_by_id.return_value = sample_user
        resp = client.delete("/api/v1/users/u-100")
        assert resp.status_code == 204

    def test_delete_user_404(self, client: TestClient, mock_repo: AsyncMock):
        mock_repo.get_by_id.return_value = None
        resp = client.delete("/api/v1/users/missing")
        assert resp.status_code == 404


# ---- GET /api/v1/users ----

class TestListUsersEndpoint:
    """Tests for GET /api/v1/users."""

    def test_list_users_200_empty(self, client: TestClient):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_users_200_with_results(
        self, client: TestClient, mock_repo: AsyncMock, sample_user: User
    ):
        mock_repo.list_by_tenant.return_value = [sample_user]
        resp = client.get("/api/v1/users?tenant_id=test-tenant&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["limit"] == 10


# ---- Health check ----

class TestHealthEndpoint:
    """Test health endpoints are registered."""

    def test_health_live(self, client: TestClient):
        resp = client.get("/health/live")
        assert resp.status_code == 200
