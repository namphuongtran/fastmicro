"""Tests for shared.fastapi_utils.dependencies — get_service_context."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.fastapi_utils.dependencies import ServiceContextDep

# ---- app fixture ----

@pytest.fixture
def app() -> FastAPI:
    """Build a minimal FastAPI app with a route using ServiceContext."""
    test_app = FastAPI()

    @test_app.get("/ctx")
    async def _ctx_route(ctx: ServiceContextDep) -> dict:
        return {
            "user_id": ctx.user_id,
            "tenant_id": ctx.tenant_id,
            "correlation_id": ctx.correlation_id,
            "roles": ctx.roles,
            "permissions": ctx.permissions,
            "metadata": ctx.metadata,
        }

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ---- Tests ----

class TestGetServiceContext:
    """Tests for get_service_context dependency."""

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_no_user_state_returns_empty_context(self, _corr, _ctx, client: TestClient):
        """Without auth middleware, context should be mostly empty."""
        resp = client.get("/ctx")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] is None
        assert data["tenant_id"] is None
        assert data["roles"] == []
        assert data["permissions"] == []

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value="corr-123")
    def test_correlation_id_from_middleware(self, _corr, _ctx, client: TestClient):
        """Correlation ID should be extracted from middleware context."""
        resp = client.get("/ctx")
        assert resp.status_code == 200
        assert resp.json()["correlation_id"] == "corr-123"

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_tenant_id_from_header(self, _corr, _ctx, client: TestClient):
        """X-Tenant-ID header should populate tenant_id."""
        resp = client.get("/ctx", headers={"X-Tenant-ID": "tenant-abc"})
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "tenant-abc"

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_dict_user_state(self, _corr, _ctx, app: FastAPI):
        """When request.state.user is a dict, extract sub/roles/permissions."""
        user_dict = {
            "sub": "user-42",
            "roles": ["admin"],
            "permissions": ["read", "write"],
            "tenant_id": "tenant-jwt",
        }

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user = user_dict
            return await call_next(request)

        with TestClient(app) as c:
            resp = c.get("/ctx")

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-42"
        assert data["roles"] == ["admin"]
        assert data["permissions"] == ["read", "write"]
        # Without X-Tenant-ID header, should fall back to JWT claim
        assert data["tenant_id"] == "tenant-jwt"

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_object_user_state(self, _corr, _ctx, app: FastAPI):
        """When request.state.user is an object with attributes, extract fields."""
        user_obj = SimpleNamespace(
            sub="user-99",
            roles=["reader"],
            permissions=["read"],
            tenant_id="tenant-obj",
        )

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user = user_obj
            return await call_next(request)

        with TestClient(app) as c:
            resp = c.get("/ctx")

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-99"
        assert data["roles"] == ["reader"]

    @patch("shared.fastapi_utils.dependencies.get_request_context", return_value=None)
    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_header_tenant_overrides_jwt_tenant(self, _corr, _ctx, app: FastAPI):
        """X-Tenant-ID header should take priority over JWT tenant claim."""
        user_dict = {"sub": "u-1", "tenant_id": "jwt-tenant"}

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user = user_dict
            return await call_next(request)

        with TestClient(app) as c:
            resp = c.get("/ctx", headers={"X-Tenant-ID": "header-tenant"})

        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "header-tenant"

    @patch("shared.fastapi_utils.dependencies.get_correlation_id", return_value=None)
    def test_request_id_in_metadata(self, _corr, app: FastAPI):
        """request_id from RequestContext should appear in metadata."""
        from shared.fastapi_utils.middleware import RequestContext

        req_ctx = RequestContext(request_id="req-777", correlation_id="c-1")

        with patch(
            "shared.fastapi_utils.dependencies.get_request_context",
            return_value=req_ctx,
        ), TestClient(app) as c:
            resp = c.get("/ctx")

        assert resp.status_code == 200
        assert resp.json()["metadata"]["request_id"] == "req-777"
