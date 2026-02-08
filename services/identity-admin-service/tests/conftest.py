"""Pytest configuration for identity-admin-service tests."""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    # Import here to avoid import issues
    from identity_admin_service.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_client_data() -> dict[str, Any]:
    """Sample OAuth client data for testing with unique name."""
    unique_id = str(uuid4())[:8]
    return {
        "client_name": f"Test Application {unique_id}",
        "client_type": "confidential",
        "description": "A test OAuth2 client",
        "redirect_uris": ["https://example.com/callback"],
        "allowed_scopes": ["openid", "profile", "email"],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "client_secret_basic",
        "access_token_lifetime": 3600,
        "refresh_token_lifetime": 86400,
        "require_pkce": True,
    }


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing with unique username/email."""
    unique_id = str(uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "SecureP@ssw0rd!",
        "roles": ["user"],
        "profile": {
            "display_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
        },
    }
