"""Pytest configuration and fixtures for identity service tests."""

from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from identity_service.configs import Settings, get_settings
from identity_service.domain.entities.client import Client, ClientScope, ClientRedirectUri
from identity_service.domain.entities.user import User, UserCredential, UserProfile
from identity_service.domain.value_objects import (
    AuthMethod,
    ClientId,
    ClientType,
    Email,
    GrantType,
    ResponseType,
    Scope,
)
from identity_service.infrastructure.security import PasswordService
from identity_service.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_env="test",
        app_port=8000,
        jwt_issuer="http://localhost:8000",
        jwt_access_token_expire_minutes=60,
        jwt_refresh_token_expire_days=30,
        database_url="sqlite+aiosqlite:///./test.db",
        redis_url="redis://localhost:6379/15",
        cors_origins=["http://localhost:3000"],
        rsa_key_size=2048,
        password_bcrypt_rounds=4,  # Lower for tests
    )


@pytest.fixture
def app(test_settings: Settings):
    """Create test FastAPI application."""
    # Override settings
    def _get_test_settings() -> Settings:
        return test_settings
    
    from identity_service import configs
    original_get_settings = configs.get_settings
    configs.get_settings = _get_test_settings
    
    application = create_app()
    
    yield application
    
    # Restore
    configs.get_settings = original_get_settings


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def password_service() -> PasswordService:
    """Create password service for tests."""
    return PasswordService(bcrypt_rounds=4)


@pytest.fixture
def test_user(password_service: PasswordService) -> User:
    """Create test user."""
    user_id = str(uuid4())
    now = datetime.now(timezone.utc)
    password_hash = password_service.hash_password("TestPassword123!")
    
    return User(
        id=user_id,
        email=Email("test@example.com"),
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
    client_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    return Client(
        id=client_id,
        client_id=ClientId("test-client"),
        name="Test Application",
        client_type=ClientType.CONFIDENTIAL,
        created_at=now,
        updated_at=now,
        allowed_grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN],
        allowed_response_types=[ResponseType.CODE],
        token_endpoint_auth_method=AuthMethod.CLIENT_SECRET_POST,
        require_pkce=True,
        scopes=[
            ClientScope(client_id=client_id, scope=Scope.OPENID),
            ClientScope(client_id=client_id, scope=Scope.PROFILE),
            ClientScope(client_id=client_id, scope=Scope.EMAIL),
        ],
        redirect_uris=[
            ClientRedirectUri(
                client_id=client_id,
                uri="http://localhost:3000/callback",
            ),
        ],
    )


@pytest.fixture
def test_public_client() -> Client:
    """Create test public OAuth client."""
    client_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    return Client(
        id=client_id,
        client_id=ClientId("test-spa"),
        name="Test SPA",
        client_type=ClientType.PUBLIC,
        created_at=now,
        updated_at=now,
        allowed_grant_types=[GrantType.AUTHORIZATION_CODE],
        allowed_response_types=[ResponseType.CODE],
        token_endpoint_auth_method=AuthMethod.NONE,
        require_pkce=True,
        scopes=[
            ClientScope(client_id=client_id, scope=Scope.OPENID),
            ClientScope(client_id=client_id, scope=Scope.PROFILE),
        ],
        redirect_uris=[
            ClientRedirectUri(
                client_id=client_id,
                uri="http://localhost:3000/callback",
            ),
        ],
    )
