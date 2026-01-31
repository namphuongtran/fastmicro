"""Unit tests for security services."""

import pytest

from identity_service.configs import Settings
from identity_service.infrastructure.security import (
    JWTService,
    KeyManager,
    PasswordService,
)


class TestPasswordService:
    """Tests for PasswordService."""

    def test_hash_password(self, password_service: PasswordService):
        """Test password hashing."""
        password = "SecurePass123!"
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)
        
        # Different hashes due to random salt
        assert hash1 != hash2
        # Both start with bcrypt prefix
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")

    def test_verify_password_correct(self, password_service: PasswordService):
        """Test verifying correct password."""
        password = "SecurePass123!"
        hashed = password_service.hash_password(password)
        
        assert password_service.verify_password(password, hashed)

    def test_verify_password_incorrect(self, password_service: PasswordService):
        """Test verifying incorrect password."""
        password = "SecurePass123!"
        hashed = password_service.hash_password(password)
        
        assert not password_service.verify_password("WrongPassword123!", hashed)

    def test_check_password_policy_valid(self, password_service: PasswordService):
        """Test valid password against policy."""
        result = password_service.check_password_policy("SecurePass123!")
        
        assert result.is_valid
        assert not result.errors

    def test_check_password_policy_too_short(self, password_service: PasswordService):
        """Test password too short."""
        result = password_service.check_password_policy("Short1!")
        
        assert not result.is_valid
        assert any("8 characters" in e for e in result.errors)

    def test_check_password_policy_no_uppercase(self, password_service: PasswordService):
        """Test password without uppercase."""
        result = password_service.check_password_policy("securepass123!")
        
        assert not result.is_valid
        assert any("uppercase" in e for e in result.errors)

    def test_needs_rehash_old_rounds(self, password_service: PasswordService):
        """Test detecting hash with old rounds."""
        # Create hash with fewer rounds
        old_service = PasswordService(bcrypt_rounds=4)
        hashed = old_service.hash_password("test")
        
        # New service with more rounds should want to rehash
        new_service = PasswordService(bcrypt_rounds=12)
        assert new_service.needs_rehash(hashed)


class TestKeyManager:
    """Tests for RSA KeyManager."""

    def test_generate_keys(self, test_settings: Settings):
        """Test RSA key generation."""
        km = KeyManager(test_settings)
        
        assert km.private_key is not None
        assert km.public_key is not None
        assert km.kid is not None

    def test_get_jwks(self, test_settings: Settings):
        """Test JWKS generation."""
        km = KeyManager(test_settings)
        jwks = km.get_jwks()
        
        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        
        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == km.kid
        assert "n" in key
        assert "e" in key


class TestJWTService:
    """Tests for JWT Service."""

    @pytest.fixture
    def jwt_service(self, test_settings: Settings) -> JWTService:
        """Create JWT service."""
        km = KeyManager(test_settings)
        return JWTService(km, test_settings)

    def test_create_access_token(self, jwt_service: JWTService):
        """Test access token creation."""
        token = jwt_service.create_access_token(
            user_id="user-123",
            client_id="my-client",
            scopes=["openid", "profile"],
        )
        
        assert token is not None
        assert token.startswith("eyJ")  # JWT header

    def test_decode_access_token(self, jwt_service: JWTService):
        """Test access token decoding."""
        token = jwt_service.create_access_token(
            user_id="user-123",
            client_id="my-client",
            scopes=["openid", "profile"],
        )
        
        payload = jwt_service.decode_token(token)
        
        assert payload["sub"] == "user-123"
        assert payload["client_id"] == "my-client"
        assert payload["scope"] == "openid profile"

    def test_create_id_token(self, jwt_service: JWTService):
        """Test ID token creation."""
        token = jwt_service.create_id_token(
            user_id="user-123",
            client_id="my-client",
            nonce="nonce-123",
            claims={
                "name": "Test User",
                "email": "test@example.com",
            },
        )
        
        assert token is not None
        payload = jwt_service.decode_token(token)
        
        assert payload["sub"] == "user-123"
        assert payload["aud"] == "my-client"
        assert payload["nonce"] == "nonce-123"
        assert payload["name"] == "Test User"

    def test_decode_invalid_token(self, jwt_service: JWTService):
        """Test decoding invalid token."""
        with pytest.raises(Exception):  # JWTError or similar
            jwt_service.decode_token("invalid.token.here")

    def test_decode_expired_token(self, jwt_service: JWTService, test_settings: Settings):
        """Test decoding expired token."""
        # Create service with very short expiry
        test_settings.jwt_access_token_expire_minutes = -1
        km = KeyManager(test_settings)
        short_jwt = JWTService(km, test_settings)
        
        token = short_jwt.create_access_token(
            user_id="user-123",
            client_id="my-client",
            scopes=["openid"],
        )
        
        # Should raise on decode
        with pytest.raises(Exception):
            short_jwt.decode_token(token)
