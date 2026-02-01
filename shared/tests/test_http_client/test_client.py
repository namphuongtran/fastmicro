"""Tests for shared.http_client.client module.

This module tests the HTTP service client implementation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from shared.http_client.client import (
    HTTPClientError,
    ServiceClient,
    ServiceClientConfig,
    ServiceResponse,
    ServiceUnavailableError,
)


class TestServiceClientConfig:
    """Tests for ServiceClientConfig."""

    def test_create_config(self) -> None:
        """Should create client config."""
        config = ServiceClientConfig(
            base_url="https://api.example.com",
            timeout=30.0,
        )

        assert config.base_url == "https://api.example.com"
        assert config.timeout == 30.0

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = ServiceClientConfig(base_url="https://api.example.com")

        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_backoff == 1.0
        assert config.retry_backoff_max == 60.0
        assert config.headers == {}

    def test_config_with_headers(self) -> None:
        """Should support default headers."""
        config = ServiceClientConfig(
            base_url="https://api.example.com",
            headers={"X-API-Key": "secret"},
        )

        assert config.headers == {"X-API-Key": "secret"}

    def test_config_with_retry_settings(self) -> None:
        """Should configure retry settings."""
        config = ServiceClientConfig(
            base_url="https://api.example.com",
            max_retries=5,
            retry_backoff=2.0,
            retry_backoff_max=120.0,
        )

        assert config.max_retries == 5
        assert config.retry_backoff == 2.0
        assert config.retry_backoff_max == 120.0


class TestServiceResponse:
    """Tests for ServiceResponse dataclass."""

    def test_create_response(self) -> None:
        """Should create service response."""
        response = ServiceResponse(
            status_code=200,
            data={"message": "success"},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.data == {"message": "success"}
        assert response.headers == {"Content-Type": "application/json"}

    def test_is_success(self) -> None:
        """Should detect successful responses."""
        success = ServiceResponse(status_code=200, data={}, headers={})
        created = ServiceResponse(status_code=201, data={}, headers={})
        error = ServiceResponse(status_code=500, data={}, headers={})

        assert success.is_success is True
        assert created.is_success is True
        assert error.is_success is False

    def test_is_client_error(self) -> None:
        """Should detect client errors."""
        bad_request = ServiceResponse(status_code=400, data={}, headers={})
        not_found = ServiceResponse(status_code=404, data={}, headers={})
        success = ServiceResponse(status_code=200, data={}, headers={})

        assert bad_request.is_client_error is True
        assert not_found.is_client_error is True
        assert success.is_client_error is False

    def test_is_server_error(self) -> None:
        """Should detect server errors."""
        internal_error = ServiceResponse(status_code=500, data={}, headers={})
        gateway_error = ServiceResponse(status_code=502, data={}, headers={})
        success = ServiceResponse(status_code=200, data={}, headers={})

        assert internal_error.is_server_error is True
        assert gateway_error.is_server_error is True
        assert success.is_server_error is False


class TestServiceClient:
    """Tests for ServiceClient class."""

    @pytest.fixture
    def config(self) -> ServiceClientConfig:
        """Create test config."""
        return ServiceClientConfig(
            base_url="https://api.example.com",
            timeout=5.0,
            max_retries=2,
        )

    @pytest.fixture
    def client(self, config: ServiceClientConfig) -> ServiceClient:
        """Create test client."""
        return ServiceClient(config)

    def test_create_client(self, config: ServiceClientConfig) -> None:
        """Should create service client."""
        client = ServiceClient(config)

        assert client is not None
        assert client.config == config

    @pytest.mark.asyncio
    async def test_get_request(self, client: ServiceClient) -> None:
        """Should make GET request."""
        mock_response = httpx.Response(
            200,
            json={"data": "value"},
            headers={"Content-Type": "application/json"},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            response = await client.get("/api/resource")

            assert response.status_code == 200
            assert response.data == {"data": "value"}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_request(self, client: ServiceClient) -> None:
        """Should make POST request with JSON body."""
        mock_response = httpx.Response(
            201,
            json={"id": 1, "name": "test"},
            headers={"Content-Type": "application/json"},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            response = await client.post(
                "/api/resource",
                json={"name": "test"},
            )

            assert response.status_code == 201
            assert response.data["id"] == 1

    @pytest.mark.asyncio
    async def test_put_request(self, client: ServiceClient) -> None:
        """Should make PUT request."""
        mock_response = httpx.Response(
            200,
            json={"id": 1, "name": "updated"},
            headers={"Content-Type": "application/json"},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            response = await client.put(
                "/api/resource/1",
                json={"name": "updated"},
            )

            assert response.status_code == 200
            assert response.data["name"] == "updated"

    @pytest.mark.asyncio
    async def test_patch_request(self, client: ServiceClient) -> None:
        """Should make PATCH request."""
        mock_response = httpx.Response(
            200,
            json={"id": 1, "status": "active"},
            headers={"Content-Type": "application/json"},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            response = await client.patch(
                "/api/resource/1",
                json={"status": "active"},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_request(self, client: ServiceClient) -> None:
        """Should make DELETE request."""
        mock_response = httpx.Response(
            204,
            content=b"",
            headers={},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            response = await client.delete("/api/resource/1")

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_custom_headers(self, client: ServiceClient) -> None:
        """Should send custom headers."""
        mock_response = httpx.Response(200, json={}, headers={})

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get(
                "/api/resource",
                headers={"Authorization": "Bearer token"},
            )

            call_kwargs = mock_request.call_args.kwargs
            assert "Authorization" in call_kwargs.get("headers", {})

    @pytest.mark.asyncio
    async def test_query_parameters(self, client: ServiceClient) -> None:
        """Should send query parameters."""
        mock_response = httpx.Response(200, json=[], headers={})

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get(
                "/api/resource",
                params={"page": 1, "limit": 10},
            )

            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs.get("params") == {"page": 1, "limit": 10}

    @pytest.mark.asyncio
    async def test_context_manager(self, config: ServiceClientConfig) -> None:
        """Should work as async context manager."""
        async with ServiceClient(config) as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_close(self, client: ServiceClient) -> None:
        """Should close client properly."""
        with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestServiceClientRetry:
    """Tests for ServiceClient retry functionality."""

    @pytest.fixture
    def config(self) -> ServiceClientConfig:
        """Create test config with retry."""
        return ServiceClientConfig(
            base_url="https://api.example.com",
            timeout=5.0,
            max_retries=3,
            retry_backoff=0.01,  # Small for fast tests
        )

    @pytest.fixture
    def client(self, config: ServiceClientConfig) -> ServiceClient:
        """Create test client."""
        return ServiceClient(config)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, client: ServiceClient) -> None:
        """Should retry on timeout."""
        success_response = httpx.Response(200, json={"ok": True}, headers={})

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                success_response,
            ]

            response = await client.get("/api/resource")

            assert response.status_code == 200
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, client: ServiceClient) -> None:
        """Should retry on connection error."""
        success_response = httpx.Response(200, json={"ok": True}, headers={})

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                httpx.ConnectError("connection refused"),
                success_response,
            ]

            response = await client.get("/api/resource")

            assert response.status_code == 200
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_5xx_error(self, client: ServiceClient) -> None:
        """Should retry on 5xx server errors."""
        # Create mock request for the responses
        mock_request = httpx.Request("GET", "https://api.example.com/api/resource")
        error_response = httpx.Response(
            503,
            json={},
            headers={},
            request=mock_request,
        )
        success_response = httpx.Response(
            200,
            json={"ok": True},
            headers={},
            request=mock_request,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [error_response, success_response]

            response = await client.get("/api/resource")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_error(self, client: ServiceClient) -> None:
        """Should not retry on 4xx client errors."""
        error_response = httpx.Response(
            404,
            json={"error": "not found"},
            headers={},
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = error_response

            response = await client.get("/api/resource")

            assert response.status_code == 404
            # Should only be called once (no retry)
            assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client: ServiceClient) -> None:
        """Should raise error when max retries exceeded."""
        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("timeout")

            with pytest.raises(ServiceUnavailableError) as exc_info:
                await client.get("/api/resource")

            assert "Max retries exceeded" in str(exc_info.value)


class TestServiceClientCorrelationId:
    """Tests for correlation ID propagation."""

    @pytest.fixture
    def config(self) -> ServiceClientConfig:
        """Create test config."""
        return ServiceClientConfig(
            base_url="https://api.example.com",
        )

    @pytest.fixture
    def client(self, config: ServiceClientConfig) -> ServiceClient:
        """Create test client."""
        return ServiceClient(config)

    @pytest.mark.asyncio
    async def test_propagate_correlation_id(self, client: ServiceClient) -> None:
        """Should propagate correlation ID in headers."""
        mock_response = httpx.Response(200, json={}, headers={})
        correlation_id = "test-correlation-123"

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get(
                "/api/resource",
                correlation_id=correlation_id,
            )

            call_kwargs = mock_request.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            assert headers.get("X-Correlation-ID") == correlation_id

    @pytest.mark.asyncio
    async def test_auto_generate_correlation_id(self, client: ServiceClient) -> None:
        """Should auto-generate correlation ID if not provided."""
        mock_response = httpx.Response(200, json={}, headers={})

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # With auto_correlation_id=True
            client_with_auto = ServiceClient(
                ServiceClientConfig(
                    base_url="https://api.example.com",
                    auto_correlation_id=True,
                )
            )

            with patch.object(client_with_auto._client, "request", new_callable=AsyncMock) as mock:
                mock.return_value = mock_response
                await client_with_auto.get("/api/resource")

                call_kwargs = mock.call_args.kwargs
                headers = call_kwargs.get("headers", {})
                assert "X-Correlation-ID" in headers


class TestHTTPClientError:
    """Tests for HTTP client errors."""

    def test_http_client_error(self) -> None:
        """Should create HTTP client error."""
        error = HTTPClientError(
            message="Request failed",
            status_code=500,
            response_data={"error": "internal"},
        )

        assert str(error) == "Request failed"
        assert error.status_code == 500
        assert error.response_data == {"error": "internal"}

    def test_service_unavailable_error(self) -> None:
        """Should create service unavailable error."""
        error = ServiceUnavailableError("Service is down")

        assert str(error) == "Service is down"
        assert isinstance(error, HTTPClientError)
