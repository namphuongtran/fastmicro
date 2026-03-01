"""Pytest configuration and fixtures for identity service tests."""

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from identity_service.configs import Settings
from identity_service.domain.entities.client import Client, ClientRedirectUri, ClientScope
from identity_service.domain.entities.user import User, UserCredential, UserProfile
from identity_service.domain.value_objects import (
    AuthMethod,
    ClientType,
    GrantType,
    ResponseType,
    Scope,
)
from identity_service.infrastructure.security import PasswordService
from identity_service.main import create_app


@pytest.fixture(scope="session")
def temp_key_dir():
    """Create temporary directory for test keys (shared across session)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def test_settings(temp_key_dir: str) -> Settings:
    """Create test settings with temporary key paths."""
    return Settings(
        app_env="test",
        app_port=8000,
        jwt_issuer="http://localhost:8000",
        jwt_audience="http://localhost:8000",
        jwt_private_key_path=str(Path(temp_key_dir) / "private.pem"),
        jwt_public_key_path=str(Path(temp_key_dir) / "public.pem"),
        database_url="sqlite+aiosqlite:///./test.db",
        redis_url="redis://localhost:6379/15",
        bcrypt_rounds=4,  # Lower for tests
    )


@pytest.fixture
def app(test_settings: Settings, monkeypatch):
    """Create test FastAPI application."""
    # Clear all caches before test to ensure fresh state
    from identity_service import configs
    from identity_service.infrastructure.security import jwt_service
    from shared.observability.health import _health_checks

    jwt_service.get_key_manager.cache_clear()
    jwt_service._jwt_service_cache.clear()
    configs.get_settings.cache_clear()
    _health_checks.clear()

    # Set environment variables for settings
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PORT", str(test_settings.app_port))
    monkeypatch.setenv("JWT_ISSUER", test_settings.jwt_issuer)
    monkeypatch.setenv("JWT_AUDIENCE", test_settings.jwt_audience)
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", test_settings.jwt_private_key_path)
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", test_settings.jwt_public_key_path)
    monkeypatch.setenv("DATABASE_URL", test_settings.database_url.get_secret_value())
    monkeypatch.setenv("REDIS_URL", test_settings.redis_url)
    monkeypatch.setenv("BCRYPT_ROUNDS", str(test_settings.bcrypt_rounds))

    # Clear the cache again after setting env vars so Settings picks them up
    configs.get_settings.cache_clear()

    application = create_app()

    yield application

    # Cleanup caches
    jwt_service.get_key_manager.cache_clear()
    jwt_service._jwt_service_cache.clear()
    configs.get_settings.cache_clear()
    _health_checks.clear()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def password_service(test_settings: Settings) -> PasswordService:
    """Create password service for tests."""
    return PasswordService(test_settings)


@pytest.fixture
def test_user(password_service: PasswordService) -> User:
    """Create test user."""
    user_id = uuid4()
    now = datetime.now(UTC)
    password_hash = password_service.hash_password("TestPassword123!")

    return User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        created_at=now,
        updated_at=now,
        credential=UserCredential(
            user_id=user_id,
            password_hash=password_hash,
            mfa_enabled=False,
        ),
        profile=UserProfile(
            user_id=user_id,
            given_name="Test",
            family_name="User",
            name="Test User",
            preferred_username="testuser",
        ),
    )


@pytest.fixture
def test_client_entity() -> Client:
    """Create test OAuth client."""
    client_uuid = uuid4()
    now = datetime.now(UTC)

    return Client(
        id=client_uuid,
        client_id="test-client",
        client_name="Test Application",
        client_type=ClientType.CONFIDENTIAL,
        created_at=now,
        updated_at=now,
        grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN],
        response_types=[ResponseType.CODE],
        token_endpoint_auth_method=AuthMethod.CLIENT_SECRET_POST,
        require_pkce=True,
        scopes=[
            ClientScope(client_id=client_uuid, scope=Scope.OPENID),
            ClientScope(client_id=client_uuid, scope=Scope.PROFILE),
            ClientScope(client_id=client_uuid, scope=Scope.EMAIL),
        ],
        redirect_uris=[
            ClientRedirectUri(
                client_id=client_uuid,
                uri="http://localhost:3000/callback",
            ),
        ],
    )


@pytest.fixture
def test_public_client() -> Client:
    """Create test public OAuth client."""
    client_uuid = uuid4()
    now = datetime.now(UTC)

    return Client(
        id=client_uuid,
        client_id="test-spa-client",
        client_name="Test SPA",
        client_type=ClientType.PUBLIC,
        created_at=now,
        updated_at=now,
        grant_types=[GrantType.AUTHORIZATION_CODE],
        response_types=[ResponseType.CODE],
        token_endpoint_auth_method=AuthMethod.NONE,
        require_pkce=True,
        scopes=[
            ClientScope(client_id=client_uuid, scope=Scope.OPENID),
            ClientScope(client_id=client_uuid, scope=Scope.PROFILE),
        ],
        redirect_uris=[
            ClientRedirectUri(
                client_id=client_uuid,
                uri="http://localhost:3000/callback",
            ),
        ],
    )
