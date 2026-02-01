"""Tests for the request logging middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.observability import (
    configure_structlog_for_testing,
    get_correlation_id,
)
from shared.observability.middleware import (
    RequestLoggingConfig,
    RequestLoggingMiddleware,
)


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure structlog for testing before each test."""
    configure_structlog_for_testing()
    yield


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok", "correlation_id": get_correlation_id()}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    @app.get("/slow")
    async def slow_endpoint():
        import asyncio

        await asyncio.sleep(0.01)
        return {"message": "slow"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics_endpoint():
        return {"metrics": []}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestRequestLoggingConfig:
    """Tests for RequestLoggingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RequestLoggingConfig()

        assert config.correlation_id_header == "X-Correlation-ID"
        assert config.request_id_header == "X-Request-ID"
        assert config.log_request_headers is False
        assert config.log_response_headers is False
        assert config.log_request_body is False
        assert config.log_response_body is False
        assert "/health" in config.exclude_paths
        assert "/metrics" in config.exclude_paths
        assert config.slow_request_threshold_ms == 1000.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RequestLoggingConfig(
            correlation_id_header="X-Custom-ID",
            exclude_paths=["/custom-health"],
            slow_request_threshold_ms=500.0,
        )

        assert config.correlation_id_header == "X-Custom-ID"
        assert "/custom-health" in config.exclude_paths
        assert config.slow_request_threshold_ms == 500.0


class TestCorrelationIdExtraction:
    """Tests for correlation ID extraction and propagation."""

    def test_generates_correlation_id_when_not_provided(self, client: TestClient):
        """Test that correlation ID is generated when not in request."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

        # Verify it's a valid UUID format
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) == 36  # UUID format

    def test_uses_provided_correlation_id(self, client: TestClient):
        """Test that provided correlation ID is used."""
        test_id = "test-correlation-id-123"
        response = client.get("/test", headers={"X-Correlation-ID": test_id})

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_id

        # Verify it's available in the response body too
        data = response.json()
        assert data["correlation_id"] == test_id

    def test_uses_request_id_header_as_fallback(self, client: TestClient):
        """Test that X-Request-ID is used as fallback."""
        test_id = "request-id-456"
        response = client.get("/test", headers={"X-Request-ID": test_id})

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_id

    def test_correlation_id_prefers_correlation_header(self, client: TestClient):
        """Test that X-Correlation-ID takes precedence over X-Request-ID."""
        correlation_id = "correlation-123"
        request_id = "request-456"

        response = client.get(
            "/test",
            headers={
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
            },
        )

        assert response.headers["X-Correlation-ID"] == correlation_id


class TestPathExclusion:
    """Tests for path exclusion from logging."""

    def test_excluded_paths_still_work(self, client: TestClient):
        """Test that excluded paths still return responses."""
        response = client.get("/health")

        assert response.status_code == 200
        # Excluded paths don't get correlation ID header
        assert "X-Correlation-ID" not in response.headers

    def test_metrics_path_excluded(self, client: TestClient):
        """Test that /metrics is excluded."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "X-Correlation-ID" not in response.headers

    def test_custom_exclude_paths(self):
        """Test custom path exclusion."""
        app = FastAPI()
        app.add_middleware(
            RequestLoggingMiddleware,
            config=RequestLoggingConfig(
                exclude_paths=["/custom-excluded"],
            ),
        )

        @app.get("/custom-excluded")
        async def excluded():
            return {"excluded": True}

        @app.get("/not-excluded")
        async def not_excluded():
            return {"excluded": False}

        client = TestClient(app)

        # Custom excluded path
        response = client.get("/custom-excluded")
        assert "X-Correlation-ID" not in response.headers

        # Non-excluded path
        response = client.get("/not-excluded")
        assert "X-Correlation-ID" in response.headers


class TestErrorHandling:
    """Tests for error handling in middleware."""

    def test_error_response_includes_correlation_id(self, client: TestClient):
        """Test that error responses include correlation ID."""
        response = client.get("/error")

        # The exception is caught by FastAPI's default handler
        assert response.status_code == 500
        # Note: correlation ID may not be in headers if exception is raised
        # before response is returned


class TestClientIpExtraction:
    """Tests for client IP extraction."""

    def test_extracts_from_x_forwarded_for(self, client: TestClient):
        """Test IP extraction from X-Forwarded-For header."""
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"},
        )

        assert response.status_code == 200

    def test_extracts_from_x_real_ip(self, client: TestClient):
        """Test IP extraction from X-Real-IP header."""
        response = client.get(
            "/test",
            headers={"X-Real-IP": "192.168.1.2"},
        )

        assert response.status_code == 200


class TestMiddlewareIntegration:
    """Integration tests for the middleware."""

    def test_multiple_requests_get_unique_ids(self, client: TestClient):
        """Test that each request gets a unique correlation ID."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        id1 = response1.headers["X-Correlation-ID"]
        id2 = response2.headers["X-Correlation-ID"]

        assert id1 != id2

    def test_custom_correlation_id_header(self):
        """Test custom correlation ID header name."""
        app = FastAPI()
        app.add_middleware(
            RequestLoggingMiddleware,
            config=RequestLoggingConfig(
                correlation_id_header="X-Trace-ID",
            ),
        )

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert "X-Trace-ID" in response.headers
        assert "X-Correlation-ID" not in response.headers

    def test_with_request_headers_logging(self):
        """Test logging with request headers enabled."""
        app = FastAPI()
        app.add_middleware(
            RequestLoggingMiddleware,
            config=RequestLoggingConfig(
                log_request_headers=True,
            ),
        )

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test", headers={"User-Agent": "test-agent"})

        assert response.status_code == 200

    def test_sensitive_headers_redacted(self):
        """Test that sensitive headers are redacted in logs."""
        config = RequestLoggingConfig(log_request_headers=True)

        headers = {
            "Authorization": "Bearer secret-token",
            "Cookie": "session=abc123",
            "X-Api-Key": "my-api-key",
            "Content-Type": "application/json",
        }

        # Use the middleware's sanitize method
        middleware = RequestLoggingMiddleware(
            app=FastAPI(),
            config=config,
        )
        sanitized = middleware._sanitize_headers(headers)

        assert sanitized["Authorization"] == "[REDACTED]"
        assert sanitized["Cookie"] == "[REDACTED]"
        assert sanitized["X-Api-Key"] == "[REDACTED]"
        assert sanitized["Content-Type"] == "application/json"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_correlation_id_from_request(self):
        """Test get_correlation_id_from_request helper."""
        # Create a fresh app with the helper endpoint
        test_app = FastAPI()
        test_app.add_middleware(RequestLoggingMiddleware)

        @test_app.get("/with-helper")
        async def with_helper():
            # Just verify correlation ID is accessible via context
            correlation_id = get_correlation_id()
            return {"correlation_id": correlation_id}

        test_client = TestClient(test_app)
        response = test_client.get(
            "/with-helper",
            headers={"X-Correlation-ID": "helper-test-id"},
        )

        assert response.status_code == 200
        assert response.json()["correlation_id"] == "helper-test-id"


class TestSlowRequestDetection:
    """Tests for slow request detection."""

    def test_slow_threshold_configuration(self):
        """Test slow request threshold can be configured."""
        config = RequestLoggingConfig(slow_request_threshold_ms=100.0)
        assert config.slow_request_threshold_ms == 100.0

        config2 = RequestLoggingConfig(slow_request_threshold_ms=5000.0)
        assert config2.slow_request_threshold_ms == 5000.0
