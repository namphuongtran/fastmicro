"""Unit tests for domain entities."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from identity_service.domain.entities.client import Client, ClientRedirectUri, ClientScope
from identity_service.domain.entities.consent import Consent, ConsentScope
from identity_service.domain.entities.token import AuthorizationCode, RefreshToken
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
from shared.utils import now_utc


class TestUser:
    """Tests for User aggregate."""

    def test_create_user(self):
        """Test user creation."""
        user_id = str(uuid4())
        now = now_utc()
        
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username="testuser",
            created_at=now,
            updated_at=now,
        )
        
        assert user.id == user_id
        assert user.email.value == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active
        assert not user.email_verified

    def test_user_with_credential(self):
        """Test user with credential."""
        user_id = str(uuid4())
        now = now_utc()
        
        credential = UserCredential(
            user_id=user_id,
            password_hash="$2b$12$hash",
            mfa_enabled=False,
        )
        
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username="testuser",
            created_at=now,
            updated_at=now,
            credential=credential,
        )
        
        assert user.credential is not None
        assert user.credential.password_hash == "$2b$12$hash"
        assert not user.credential.mfa_enabled

    def test_user_account_lockout(self):
        """Test user account lockout after failed attempts."""
        user_id = str(uuid4())
        now = now_utc()
        
        credential = UserCredential(
            user_id=user_id,
            password_hash="$2b$12$hash",
            failed_login_attempts=5,
            locked_until=now + timedelta(minutes=15),
        )
        
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username="testuser",
            created_at=now,
            updated_at=now,
            credential=credential,
        )
        
        assert user.credential.is_locked()
        
    def test_user_lockout_expired(self):
        """Test user lockout expiration."""
        user_id = str(uuid4())
        now = now_utc()
        
        credential = UserCredential(
            user_id=user_id,
            password_hash="$2b$12$hash",
            failed_login_attempts=5,
            locked_until=now - timedelta(minutes=1),  # Past
        )
        
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            username="testuser",
            created_at=now,
            updated_at=now,
            credential=credential,
        )
        
        assert not user.credential.is_locked()


class TestClient:
    """Tests for Client aggregate."""

    def test_create_confidential_client(self):
        """Test confidential client creation."""
        client_id = str(uuid4())
        now = now_utc()
        
        client = Client(
            id=client_id,
            client_id="my-client-id",
            client_name="My Application",
            client_type=ClientType.CONFIDENTIAL,
            created_at=now,
            updated_at=now,
            grant_types=[GrantType.AUTHORIZATION_CODE],
            response_types=[ResponseType.CODE],
            token_endpoint_auth_method=AuthMethod.CLIENT_SECRET_POST,
        )
        
        assert client.client_id == "my-client-id"
        assert client.client_type == ClientType.CONFIDENTIAL
        assert client.is_active
        assert GrantType.AUTHORIZATION_CODE in client.grant_types

    def test_create_public_client(self):
        """Test public client creation."""
        client_id = str(uuid4())
        now = now_utc()
        
        client = Client(
            id=client_id,
            client_id="spa-client-id",
            client_name="SPA Application",
            client_type=ClientType.PUBLIC,
            created_at=now,
            updated_at=now,
            require_pkce=True,
            token_endpoint_auth_method=AuthMethod.NONE,
        )
        
        assert client.client_type == ClientType.PUBLIC
        assert client.require_pkce

    def test_client_with_scopes(self):
        """Test client with allowed scopes."""
        client_id = str(uuid4())
        now = now_utc()
        
        scopes = [
            ClientScope(client_id=client_id, scope=Scope.OPENID),
            ClientScope(client_id=client_id, scope=Scope.PROFILE),
        ]
        
        client = Client(
            id=client_id,
            client_id="my-client-id",
            client_name="My Application",
            client_type=ClientType.CONFIDENTIAL,
            created_at=now,
            updated_at=now,
            scopes=scopes,
        )
        
        assert len(client.scopes) == 2
        assert any(s.scope == Scope.OPENID for s in client.scopes)

    def test_client_validate_redirect_uri(self):
        """Test client redirect URI validation."""
        client_id = str(uuid4())
        now = now_utc()
        
        redirect_uris = [
            ClientRedirectUri(client_id=client_id, uri="https://example.com/callback"),
            ClientRedirectUri(client_id=client_id, uri="http://localhost:3000/callback"),
        ]
        
        client = Client(
            id=client_id,
            client_id="my-client-id",
            client_name="My Application",
            client_type=ClientType.CONFIDENTIAL,
            created_at=now,
            updated_at=now,
            redirect_uris=redirect_uris,
        )
        
        assert client.validate_redirect_uri("https://example.com/callback")
        assert client.validate_redirect_uri("http://localhost:3000/callback")
        assert client.validate_redirect_uri("https://evil.com/callback") is None


class TestAuthorizationCode:
    """Tests for AuthorizationCode entity."""

    def test_create_authorization_code(self):
        """Test authorization code creation."""
        now = now_utc()
        
        code = AuthorizationCode(
            code="abc123",
            client_id="my-client",
            user_id=uuid4(),
            redirect_uri="https://example.com/callback",
            scope="openid profile",
            expires_at=now + timedelta(minutes=10),
            created_at=now,
        )
        
        assert code.code == "abc123"
        assert code.client_id == "my-client"
        assert not code.is_expired()
        assert not code.is_used

    def test_authorization_code_expired(self):
        """Test expired authorization code."""
        now = now_utc()
        
        code = AuthorizationCode(
            code="abc123",
            client_id="my-client",
            user_id=uuid4(),
            redirect_uri="https://example.com/callback",
            scope="openid",
            expires_at=now - timedelta(minutes=1),
            created_at=now - timedelta(minutes=11),
        )
        
        assert code.is_expired()

    def test_authorization_code_with_pkce(self):
        """Test authorization code with PKCE."""
        import base64
        import hashlib
        
        verifier = "my_code_verifier_123456789012345678901234567890"
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        
        now = now_utc()
        
        code = AuthorizationCode(
            code="abc123",
            client_id="my-client",
            user_id=uuid4(),
            redirect_uri="https://example.com/callback",
            scope="openid",
            expires_at=now + timedelta(minutes=10),
            created_at=now,
            code_challenge=challenge,
            code_challenge_method="S256",
        )
        
        assert code.verify_pkce(verifier)
        assert not code.verify_pkce("wrong_verifier")


class TestRefreshToken:
    """Tests for RefreshToken entity."""

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        now = now_utc()
        
        token = RefreshToken(
            token="refresh_token_123",
            client_id="my-client",
            user_id=uuid4(),
            scope="openid offline_access",
            expires_at=now + timedelta(days=30),
            issued_at=now,
        )
        
        assert token.token == "refresh_token_123"
        assert not token.is_revoked
        assert not token.is_expired()

    def test_refresh_token_rotation(self):
        """Test refresh token rotation tracking."""
        now = now_utc()
        
        original_token = RefreshToken(
            token="original_token",
            client_id="my-client",
            user_id=uuid4(),
            scope="openid",
            expires_at=now + timedelta(days=30),
            issued_at=now,
        )
        
        rotated_token = RefreshToken(
            token="rotated_token",
            client_id="my-client",
            user_id=uuid4(),
            scope="openid",
            expires_at=now + timedelta(days=30),
            issued_at=now,
            parent_token="original_token",
        )
        
        assert rotated_token.parent_token == "original_token"


class TestConsent:
    """Tests for Consent aggregate."""

    def test_create_consent(self):
        """Test consent creation."""
        consent_id = str(uuid4())
        now = now_utc()
        
        consent = Consent(
            id=consent_id,
            user_id=uuid4(),
            client_id="my-client",
            created_at=now,
            expires_at=now + timedelta(days=365),
            scopes=[
                ConsentScope(consent_id=consent_id, scope="openid"),
                ConsentScope(consent_id=consent_id, scope="profile"),
            ],
        )
        
        assert consent.client_id == "my-client"
        assert len(consent.scopes) == 2
        assert consent.is_valid()

    def test_consent_covers_scopes(self):
        """Test consent scope coverage check."""
        consent_id = str(uuid4())
        now = now_utc()
        
        consent = Consent(
            id=consent_id,
            user_id=uuid4(),
            client_id="my-client",
            created_at=now,
            expires_at=now + timedelta(days=365),
            scopes=[
                ConsentScope(consent_id=consent_id, scope="openid"),
                ConsentScope(consent_id=consent_id, scope="profile"),
                ConsentScope(consent_id=consent_id, scope="email"),
            ],
        )
        
        assert consent.covers_scopes(["openid"])
        assert consent.covers_scopes(["openid", "profile"])
        assert not consent.covers_scopes(["openid", "offline_access"])
