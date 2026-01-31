"""
Pytest configuration and shared fixtures for the shared library test suite.

This module provides common test fixtures, configuration, and utilities
used across all test modules in the shared library.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest


# ============================================================================
# Async Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Exception Testing Fixtures
# ============================================================================


@pytest.fixture
def sample_error_context() -> dict[str, Any]:
    """Provide sample error context for exception testing."""
    return {
        "user_id": "user_123",
        "request_id": "req_abc456",
        "trace_id": "trace_xyz789",
        "operation": "test_operation",
    }


@pytest.fixture
def sample_validation_errors() -> list[dict[str, Any]]:
    """Provide sample validation errors for testing."""
    return [
        {
            "loc": ("body", "email"),
            "msg": "value is not a valid email address",
            "type": "value_error.email",
        },
        {
            "loc": ("body", "age"),
            "msg": "ensure this value is greater than 0",
            "type": "value_error.number.not_gt",
            "ctx": {"limit_value": 0},
        },
    ]


# ============================================================================
# Constants Testing Fixtures
# ============================================================================


@pytest.fixture
def all_http_status_codes() -> list[int]:
    """Provide all standard HTTP status codes for testing."""
    return [
        # 2xx Success
        200, 201, 202, 204,
        # 3xx Redirection
        301, 302, 304, 307, 308,
        # 4xx Client Errors
        400, 401, 403, 404, 405, 409, 422, 429,
        # 5xx Server Errors
        500, 502, 503, 504,
    ]


# ============================================================================
# Utility Testing Fixtures
# ============================================================================


@pytest.fixture
def sample_nested_dict() -> dict[str, Any]:
    """Provide sample nested dictionary for serialization testing."""
    return {
        "user": {
            "id": 123,
            "name": "Test User",
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "tags": ["admin", "active"],
            },
        },
        "items": [
            {"id": 1, "value": "item1"},
            {"id": 2, "value": "item2"},
        ],
    }


# ============================================================================
# Async Testing Utilities
# ============================================================================


@pytest.fixture
async def async_context() -> AsyncGenerator[dict[str, Any], None]:
    """Provide async context for testing async operations."""
    context = {"initialized": True, "count": 0}
    yield context
    # Cleanup
    context["initialized"] = False
