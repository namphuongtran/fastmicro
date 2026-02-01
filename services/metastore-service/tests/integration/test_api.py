"""Integration tests for Metastore API."""

import pytest
from fastapi.testclient import TestClient

from metastore_service.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoints:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "metastore-service"

    def test_readiness_check(self, client):
        response = client.get("/health/ready")
        assert response.status_code == 200


@pytest.mark.skip(reason="Requires database setup - run with integration test config")
class TestMetadataEndpoints:
    """Integration tests for metadata API endpoints.

    These tests require a running database. To run them:
    1. Set DATABASE_URL environment variable
    2. Run: pytest tests/integration/test_api.py::TestMetadataEndpoints -v
    """

    def test_create_metadata(self, client):
        response = client.post(
            "/api/v1/metadata", json={"key": "test-key", "value": {"foo": "bar"}}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "test-key"
        assert data["value"] == {"foo": "bar"}
        assert data["version"] == 1

    def test_get_metadata(self, client):
        client.post("/api/v1/metadata", json={"key": "get-test", "value": 123})
        response = client.get("/api/v1/metadata/get-test")
        assert response.status_code == 200
        assert response.json()["value"] == 123

    def test_update_metadata(self, client):
        client.post("/api/v1/metadata", json={"key": "update-test", "value": "old"})
        response = client.put("/api/v1/metadata/update-test", json={"value": "new"})
        assert response.status_code == 200
        assert response.json()["value"] == "new"
        assert response.json()["version"] == 2

    def test_delete_metadata(self, client):
        client.post("/api/v1/metadata", json={"key": "delete-test", "value": "x"})
        response = client.delete("/api/v1/metadata/delete-test")
        assert response.status_code == 204

    def test_get_not_found(self, client):
        response = client.get("/api/v1/metadata/nonexistent")
        assert response.status_code == 404
