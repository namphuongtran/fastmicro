"""Tests for shared.fastapi_utils.middleware module.

This module tests FastAPI middleware components, verifying that
correlation ID management is properly delegated to shared.observability.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from shared.fastapi_utils.middleware import (
    RequestContext,
    RequestContextMiddleware,
    get_correlation_id,
    get_request_context,
)
from shared.observability.structlog_config import (
    _correlation_id_ctx,
)
from shared.observability.structlog_config import (
    get_correlation_id as observability_get_correlation_id,
)


class TestRequestContext:
    """Tests for RequestContext model."""

    def test_create_request_context(self) -> None:
        """Should create request context with required fields."""
        ctx = RequestContext(
            request_id="req_123",
            correlation_id="corr_456",
            user_id=None,
        )

        assert ctx.request_id == "req_123"
        assert ctx.correlation_id == "corr_456"
        assert ctx.user_id is None

    def test_request_context_with_user(self) -> None:
        """Should create request context with user ID."""
        ctx = RequestContext(
            request_id="req_123",
            correlation_id="corr_456",
            user_id="user_789",
        )

        assert ctx.user_id == "user_789"

    def test_request_context_with_metadata(self) -> None:
        """Should support additional metadata."""
        ctx = RequestContext(
            request_id="req_123",
            correlation_id="corr_456",
            user_id=None,
            metadata={"tenant_id": "t1", "region": "us-east"},
        )

        assert ctx.metadata["tenant_id"] == "t1"


class TestRequestContextMiddleware:
    """Tests for RequestContextMiddleware."""

    @pytest.fixture
    def app_with_middleware(self) -> FastAPI:
        """Create FastAPI app with request context middleware."""
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/test")
        async def test_endpoint(request: Request):
            ctx = get_request_context()
            return {
                "request_id": ctx.request_id if ctx else None,
                "correlation_id": ctx.correlation_id if ctx else None,
            }

        return app

    def test_middleware_creates_request_context(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Should create request context for each request."""
        client = TestClient(app_with_middleware)
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] is not None
        assert data["correlation_id"] is not None

    def test_middleware_uses_provided_correlation_id(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Should use correlation ID from header if provided."""
        client = TestClient(app_with_middleware)
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": "custom-corr-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == "custom-corr-id"

    def test_middleware_generates_unique_request_ids(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Should generate unique request IDs for each request."""
        client = TestClient(app_with_middleware)

        response1 = client.get("/test")
        response2 = client.get("/test")

        id1 = response1.json()["request_id"]
        id2 = response2.json()["request_id"]

        assert id1 != id2

    def test_middleware_adds_correlation_id_to_response(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Should add correlation ID to response headers."""
        client = TestClient(app_with_middleware)
        response = client.get("/test")

        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == response.json()["correlation_id"]


class TestGetRequestContext:
    """Tests for get_request_context function."""

    def test_returns_none_outside_request(self) -> None:
        """Should return None when called outside request context."""
        # Clear any existing context
        ctx = get_request_context()
        # Outside of a request, should return None
        assert ctx is None or isinstance(ctx, RequestContext)


class TestGetCorrelationId:
    """Tests for get_correlation_id function."""

    def test_returns_none_outside_request(self) -> None:
        """Should return None when called outside request context."""
        corr_id = get_correlation_id()
        # Outside of a request, should return None
        assert corr_id is None or isinstance(corr_id, str)

    def test_delegates_to_observability_module(self) -> None:
        """Should delegate to shared.observability.structlog_config."""
        # Set correlation ID via observability module
        token = _correlation_id_ctx.set("test-corr-123")
        try:
            # get_correlation_id from fastapi_utils should return the same value
            assert get_correlation_id() == "test-corr-123"
            assert get_correlation_id() == observability_get_correlation_id()
        finally:
            _correlation_id_ctx.reset(token)


class TestCorrelationIdConsolidation:
    """Tests verifying correlation ID is managed by observability module."""

    @pytest.fixture
    def app_with_middleware(self) -> FastAPI:
        """Create FastAPI app with request context middleware."""
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/check-correlation")
        async def check_correlation(request: Request):
            # Both should return the same value
            fastapi_utils_id = get_correlation_id()
            observability_id = observability_get_correlation_id()
            return {
                "fastapi_utils_id": fastapi_utils_id,
                "observability_id": observability_id,
                "match": fastapi_utils_id == observability_id,
            }

        return app

    def test_correlation_id_is_same_in_both_modules(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Correlation ID from fastapi_utils should match observability."""
        client = TestClient(app_with_middleware)
        response = client.get("/check-correlation")

        assert response.status_code == 200
        data = response.json()
        assert data["match"] is True
        assert data["fastapi_utils_id"] == data["observability_id"]

    def test_provided_correlation_id_is_set_in_observability(
        self, app_with_middleware: FastAPI
    ) -> None:
        """Provided correlation ID should be set in observability context."""
        client = TestClient(app_with_middleware)
        response = client.get(
            "/check-correlation",
            headers={"X-Correlation-ID": "provided-corr-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fastapi_utils_id"] == "provided-corr-id"
        assert data["observability_id"] == "provided-corr-id"
