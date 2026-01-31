"""Tests for shared.auth.jwt module.

This module tests JWT token creation, verification, and management.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from shared.auth.jwt import (
    JWTService,
    TokenData,
    TokenType,
    InvalidTokenError,
    ExpiredTokenError,
)


class TestTokenType:
    """Tests for TokenType enum."""

    def test_access_token_type(self) -> None:
        """Should have access token type."""
        assert TokenType.ACCESS.value == "access"

    def test_refresh_token_type(self) -> None:
        """Should have refresh token type."""
        assert TokenType.REFRESH.value == "refresh"


class TestTokenData:
    """Tests for TokenData model."""

    def test_create_token_data(self) -> None:
        """Should create token data with required fields."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        
        assert data.sub == "user123"
        assert data.scopes == []
        assert data.token_type == TokenType.ACCESS

    def test_token_data_with_scopes(self) -> None:
        """Should create token data with scopes."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            scopes=["read", "write"],
        )
        
        assert data.scopes == ["read", "write"]

    def test_token_data_with_custom_claims(self) -> None:
        """Should support custom claims."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            custom_claims={"role": "admin", "tenant_id": "t1"},
        )
        
        assert data.custom_claims["role"] == "admin"

    def test_is_expired_false(self) -> None:
        """Should return False when token is not expired."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        
        assert data.is_expired is False

    def test_is_expired_true(self) -> None:
        """Should return True when token is expired."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) - timedelta(hours=1),
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        
        assert data.is_expired is True

    def test_has_scope_true(self) -> None:
        """Should return True when scope is present."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            scopes=["read", "write"],
        )
        
        assert data.has_scope("read") is True
        assert data.has_scope("write") is True

    def test_has_scope_false(self) -> None:
        """Should return False when scope is not present."""
        data = TokenData(
            sub="user123",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            scopes=["read"],
        )
        
        assert data.has_scope("admin") is False


class TestJWTService:
    """Tests for JWTService class."""

    @pytest.fixture
    def jwt_service(self) -> JWTService:
        """Create JWT service with test secret."""
        return JWTService(
            secret_key="test-secret-key-for-testing-only-32chars",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    def test_create_access_token(self, jwt_service: JWTService) -> None:
        """Should create access token."""
        token = jwt_service.create_access_token(subject="user123")
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_scopes(self, jwt_service: JWTService) -> None:
        """Should create access token with scopes."""
        token = jwt_service.create_access_token(
            subject="user123",
            scopes=["read", "write"],
        )
        
        data = jwt_service.verify_token(token)
        assert "read" in data.scopes
        assert "write" in data.scopes

    def test_create_access_token_with_custom_claims(
        self, jwt_service: JWTService
    ) -> None:
        """Should create access token with custom claims."""
        token = jwt_service.create_access_token(
            subject="user123",
            custom_claims={"role": "admin"},
        )
        
        data = jwt_service.verify_token(token)
        assert data.custom_claims["role"] == "admin"

    def test_create_refresh_token(self, jwt_service: JWTService) -> None:
        """Should create refresh token."""
        token = jwt_service.create_refresh_token(subject="user123")
        
        assert isinstance(token, str)
        data = jwt_service.verify_token(token)
        assert data.token_type == TokenType.REFRESH

    def test_verify_valid_token(self, jwt_service: JWTService) -> None:
        """Should verify valid token."""
        token = jwt_service.create_access_token(subject="user123")
        
        data = jwt_service.verify_token(token)
        
        assert data.sub == "user123"
        assert data.token_type == TokenType.ACCESS

    def test_verify_invalid_token(self, jwt_service: JWTService) -> None:
        """Should raise for invalid token."""
        with pytest.raises(InvalidTokenError):
            jwt_service.verify_token("invalid.token.here")

    def test_verify_expired_token(self, jwt_service: JWTService) -> None:
        """Should raise for expired token."""
        # Create service with very short expiry
        short_service = JWTService(
            secret_key="test-secret-key-for-testing-only-32chars",
            access_token_expire_minutes=0,  # Immediate expiry
        )
        
        # Create token (will be immediately expired)
        token = short_service.create_access_token(subject="user123")
        
        # Wait a moment
        time.sleep(0.1)
        
        with pytest.raises(ExpiredTokenError):
            short_service.verify_token(token)

    def test_verify_wrong_secret(self) -> None:
        """Should raise for token signed with different secret."""
        service1 = JWTService(secret_key="secret-key-1-long-enough-32chars")
        service2 = JWTService(secret_key="secret-key-2-long-enough-32chars")
        
        token = service1.create_access_token(subject="user123")
        
        with pytest.raises(InvalidTokenError):
            service2.verify_token(token)

    def test_decode_without_verification(self, jwt_service: JWTService) -> None:
        """Should decode token without verification."""
        token = jwt_service.create_access_token(subject="user123")
        
        data = jwt_service.decode_token(token, verify=False)
        
        assert data.sub == "user123"

    def test_access_token_expiry(self, jwt_service: JWTService) -> None:
        """Should set correct expiry for access token."""
        token = jwt_service.create_access_token(subject="user123")
        data = jwt_service.verify_token(token)
        
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=30)
        # Allow 5 second tolerance
        assert abs((data.exp - expected_exp).total_seconds()) < 5

    def test_refresh_token_expiry(self, jwt_service: JWTService) -> None:
        """Should set correct expiry for refresh token."""
        token = jwt_service.create_refresh_token(subject="user123")
        data = jwt_service.verify_token(token)
        
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)
        # Allow 5 second tolerance
        assert abs((data.exp - expected_exp).total_seconds()) < 5

    def test_issuer_claim(self) -> None:
        """Should include issuer claim when configured."""
        service = JWTService(
            secret_key="test-secret-key-for-testing-only-32chars",
            issuer="https://auth.example.com",
        )
        
        token = service.create_access_token(subject="user123")
        data = service.verify_token(token)
        
        assert data.iss == "https://auth.example.com"

    def test_audience_claim(self) -> None:
        """Should include audience claim when configured."""
        service = JWTService(
            secret_key="test-secret-key-for-testing-only-32chars",
            audience="https://api.example.com",
        )
        
        token = service.create_access_token(subject="user123")
        data = service.verify_token(token)
        
        assert data.aud == "https://api.example.com"

    def test_custom_expiry(self, jwt_service: JWTService) -> None:
        """Should support custom expiry time."""
        custom_expiry = timedelta(hours=2)
        token = jwt_service.create_access_token(
            subject="user123",
            expires_delta=custom_expiry,
        )
        
        data = jwt_service.verify_token(token)
        expected_exp = datetime.now(timezone.utc) + custom_expiry
        assert abs((data.exp - expected_exp).total_seconds()) < 5


class TestInvalidTokenError:
    """Tests for InvalidTokenError exception."""

    def test_invalid_token_error(self) -> None:
        """Should create invalid token error."""
        error = InvalidTokenError("Token signature invalid")
        
        assert str(error) == "Token signature invalid"
        assert isinstance(error, Exception)


class TestExpiredTokenError:
    """Tests for ExpiredTokenError exception."""

    def test_expired_token_error(self) -> None:
        """Should create expired token error."""
        error = ExpiredTokenError("Token has expired")
        
        assert str(error) == "Token has expired"
        assert isinstance(error, InvalidTokenError)
