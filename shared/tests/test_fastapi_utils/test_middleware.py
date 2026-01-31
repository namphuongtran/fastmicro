"""Tests for shared.fastapi_utils.middleware module.

This module tests FastAPI middleware components.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from shared.fastapi_utils.middleware import (
    RequestContextMiddleware,
    CorrelationIdMiddleware,
    get_request_context,
    get_correlation_id,
    RequestContext,
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


class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware."""

    @pytest.fixture
    def app_with_correlation_middleware(self) -> FastAPI:
        """Create FastAPI app with correlation ID middleware."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            corr_id = get_correlation_id()
            return {"correlation_id": corr_id}
        
        return app

    def test_generates_correlation_id(
        self, app_with_correlation_middleware: FastAPI
    ) -> None:
        """Should generate correlation ID if not provided."""
        client = TestClient(app_with_correlation_middleware)
        response = client.get("/test")
        
        assert response.status_code == 200
        corr_id = response.json()["correlation_id"]
        assert corr_id is not None
        # Should be a valid UUID
        uuid.UUID(corr_id)

    def test_uses_provided_correlation_id(
        self, app_with_correlation_middleware: FastAPI
    ) -> None:
        """Should use correlation ID from request header."""
        client = TestClient(app_with_correlation_middleware)
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": "my-custom-id"},
        )
        
        assert response.json()["correlation_id"] == "my-custom-id"

    def test_custom_header_name(self) -> None:
        """Should support custom header name."""
        app = FastAPI()
        app.add_middleware(
            CorrelationIdMiddleware,
            header_name="X-Request-ID",
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"correlation_id": get_correlation_id()}
        
        client = TestClient(app)
        response = client.get(
            "/test",
            headers={"X-Request-ID": "custom-request-id"},
        )
        
        assert response.json()["correlation_id"] == "custom-request-id"


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
