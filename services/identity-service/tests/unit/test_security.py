"""Unit tests for security services."""

from pathlib import Path

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
        """Test password hashing with Argon2."""
        password = "SecurePass123!"
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)

        # Different hashes due to random salt
        assert hash1 != hash2
        # Both start with Argon2 prefix (new default)
        assert hash1.startswith("$argon2")
        assert hash2.startswith("$argon2")

    def test_verify_password_correct(self, password_service: PasswordService):
        """Test verifying correct password."""
        password = "SecurePass123!"
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed)

    def test_verify_password_bcrypt_backward_compat(self, password_service: PasswordService):
        """Test verifying legacy bcrypt password hash (migration support)."""
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher

        password = "SecurePass123!"
        # Simulate a legacy bcrypt hash (as if from old passlib)
        legacy_hasher = PasswordHash((BcryptHasher(rounds=4),))
        bcrypt_hash = legacy_hasher.hash(password)

        # Service should still verify bcrypt hashes (backward compatibility)
        assert password_service.verify_password(password, bcrypt_hash)

    def test_verify_password_incorrect(self, password_service: PasswordService):
        """Test verifying incorrect password."""
        password = "SecurePass123!"
        hashed = password_service.hash_password(password)

        assert not password_service.verify_password("WrongPassword123!", hashed)

    def test_validate_password_valid(self, password_service: PasswordService):
        """Test valid password against policy."""
        errors = password_service.validate_password("SecurePass123!")

        assert len(errors) == 0

    def test_validate_password_too_short(self, password_service: PasswordService):
        """Test password too short."""
        errors = password_service.validate_password("Short1!")

        assert len(errors) > 0
        assert any("12 characters" in e for e in errors)

    def test_validate_password_no_uppercase(self, password_service: PasswordService):
        """Test password without uppercase."""
        errors = password_service.validate_password("securepassword123!")

        assert len(errors) > 0
        assert any("uppercase" in e for e in errors)

    def test_needs_rehash_bcrypt_to_argon2(self, test_settings: Settings):
        """Test detecting legacy bcrypt hash that needs upgrade to Argon2."""
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher

        # Simulate a legacy bcrypt hash (as if from old passlib)
        legacy_hasher = PasswordHash((BcryptHasher(rounds=4),))
        bcrypt_hash = legacy_hasher.hash("test")

        # New service should detect bcrypt needs rehash to Argon2
        new_settings = Settings(
            app_env="test",
            bcrypt_rounds=12,
            database_url="sqlite+aiosqlite:///./test.db",
        )
        new_service = PasswordService(new_settings)
        assert new_service.needs_rehash(bcrypt_hash)

        # But Argon2 hashes should not need rehash
        argon2_hash = new_service.hash_password("test")
        assert not new_service.needs_rehash(argon2_hash)


class TestKeyManager:
    """Tests for RSA KeyManager."""

    def test_generate_keys(self, tmp_path: Path):
        """Test RSA key generation."""
        private_key_path = tmp_path / "private.pem"
        public_key_path = tmp_path / "public.pem"

        km = KeyManager(str(private_key_path), str(public_key_path))

        assert km.private_key is not None
        assert km.public_key is not None
        assert km.kid is not None

    def test_get_jwks(self, tmp_path: Path):
        """Test JWKS generation."""
        private_key_path = tmp_path / "private.pem"
        public_key_path = tmp_path / "public.pem"

        km = KeyManager(str(private_key_path), str(public_key_path))
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
    def jwt_service(self, test_settings: Settings, tmp_path: Path) -> JWTService:
        """Create JWT service."""
        private_key_path = tmp_path / "private.pem"
        public_key_path = tmp_path / "public.pem"
        km = KeyManager(str(private_key_path), str(public_key_path))
        return JWTService(test_settings, km)

    def test_create_access_token(self, jwt_service: JWTService):
        """Test access token creation."""
        token, jti, expires_in = jwt_service.create_access_token(
            subject="user-123",
            client_id="my-client",
            scope="openid profile",
        )

        assert token is not None
        assert token.startswith("eyJ")  # JWT header
        assert jti is not None
        assert expires_in > 0

    def test_decode_access_token(self, jwt_service: JWTService):
        """Test access token decoding."""
        token, _, _ = jwt_service.create_access_token(
            subject="user-123",
            client_id="my-client",
            scope="openid profile",
        )

        payload = jwt_service.decode_token(token)

        assert payload["sub"] == "user-123"
        assert payload["client_id"] == "my-client"
        assert payload["scope"] == "openid profile"

    def test_create_id_token(self, jwt_service: JWTService):
        """Test ID token creation."""
        token = jwt_service.create_id_token(
            subject="user-123",
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
        # decode_token returns None for invalid tokens instead of raising
        result = jwt_service.decode_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self, test_settings: Settings, tmp_path: Path):
        """Test decoding expired token."""
        # Create service with very short expiry
        test_settings.access_token_lifetime = -1
        private_key_path = tmp_path / "private.pem"
        public_key_path = tmp_path / "public.pem"
        km = KeyManager(str(private_key_path), str(public_key_path))
        short_jwt = JWTService(test_settings, km)

        token, _, _ = short_jwt.create_access_token(
            subject="user-123",
            client_id="my-client",
            scope="openid",
        )

        # Should return None for expired token
        result = short_jwt.decode_token(token)
        assert result is None
