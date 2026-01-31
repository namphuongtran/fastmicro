"""Tests for shared.fastapi_utils.exception_handlers module.

This module tests FastAPI exception handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.exceptions import (
    NotFoundException,
    ValidationException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    DatabaseException,
    ServiceUnavailableException,
)
from shared.fastapi_utils.exception_handlers import (
    register_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
)


class TestExceptionHandlers:
    """Tests for exception handlers."""

    @pytest.fixture
    def app_with_handlers(self) -> FastAPI:
        """Create FastAPI app with exception handlers."""
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/not-found")
        async def raise_not_found():
            raise NotFoundException.for_resource("User", "123")
        
        @app.get("/validation-error")
        async def raise_validation():
            raise ValidationException(
                message="Invalid input",
                errors=[],
            )
        
        @app.get("/unauthorized")
        async def raise_unauthorized():
            raise UnauthorizedException("Authentication required")
        
        @app.get("/forbidden")
        async def raise_forbidden():
            raise ForbiddenException("Access denied")
        
        @app.get("/conflict")
        async def raise_conflict():
            raise ConflictException("Resource already exists")
        
        @app.get("/database-error")
        async def raise_database_error():
            raise DatabaseException("Database connection failed")
        
        @app.get("/service-unavailable")
        async def raise_service_unavailable():
            raise ServiceUnavailableException("Service temporarily unavailable")
        
        return app

    def test_not_found_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 404 for NotFoundException."""
        client = TestClient(app_with_handlers)
        response = client.get("/not-found")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert "not found" in data["error"]["message"].lower()

    def test_validation_error_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 422 for ValidationError."""
        client = TestClient(app_with_handlers)
        response = client.get("/validation-error")
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_unauthorized_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 401 for UnauthorizedError."""
        client = TestClient(app_with_handlers)
        response = client.get("/unauthorized")
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_forbidden_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 403 for ForbiddenError."""
        client = TestClient(app_with_handlers)
        response = client.get("/forbidden")
        
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN"

    def test_conflict_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 409 for ConflictError."""
        client = TestClient(app_with_handlers)
        response = client.get("/conflict")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "CONFLICT"

    def test_database_error_handler(self, app_with_handlers: FastAPI) -> None:
        """Should return 500 for DatabaseException (internal error)."""
        client = TestClient(app_with_handlers)
        response = client.get("/database-error")
        
        # DatabaseException defaults to 500 as it's an internal error
        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    def test_service_unavailable_handler(
        self, app_with_handlers: FastAPI
    ) -> None:
        """Should return 503 for ServiceUnavailableError."""
        client = TestClient(app_with_handlers)
        response = client.get("/service-unavailable")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"

    def test_error_response_format(self, app_with_handlers: FastAPI) -> None:
        """Should return consistent error response format."""
        client = TestClient(app_with_handlers)
        response = client.get("/not-found")
        
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]


class TestUnhandledExceptions:
    """Tests for unhandled exception behavior."""

    @pytest.fixture
    def app_with_handlers(self) -> FastAPI:
        """Create FastAPI app with exception handlers."""
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/generic-error")
        async def raise_generic():
            raise RuntimeError("Something went wrong")
        
        return app

    def test_generic_exception_handler(
        self, app_with_handlers: FastAPI
    ) -> None:
        """Should return 500 for unhandled exceptions."""
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        response = client.get("/generic-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
