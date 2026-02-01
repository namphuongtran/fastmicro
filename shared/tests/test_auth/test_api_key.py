"""Tests for shared.auth.api_key module.

This module tests API key generation and validation.
"""

from __future__ import annotations

import pytest

from shared.auth.api_key import (
    APIKeyData,
    APIKeyService,
    InvalidAPIKeyError,
)


class TestAPIKeyData:
    """Tests for APIKeyData model."""

    def test_create_api_key_data(self) -> None:
        """Should create API key data."""
        data = APIKeyData(
            key_id="key_123",
            name="Test API Key",
            scopes=["read", "write"],
        )

        assert data.key_id == "key_123"
        assert data.name == "Test API Key"
        assert data.scopes == ["read", "write"]
        assert data.is_active is True

    def test_api_key_data_defaults(self) -> None:
        """Should have sensible defaults."""
        data = APIKeyData(
            key_id="key_123",
            name="Test Key",
        )

        assert data.scopes == []
        assert data.is_active is True
        assert data.metadata == {}

    def test_has_scope_true(self) -> None:
        """Should return True when scope is present."""
        data = APIKeyData(
            key_id="key_123",
            name="Test Key",
            scopes=["read", "write"],
        )

        assert data.has_scope("read") is True

    def test_has_scope_false(self) -> None:
        """Should return False when scope is not present."""
        data = APIKeyData(
            key_id="key_123",
            name="Test Key",
            scopes=["read"],
        )

        assert data.has_scope("admin") is False


class TestAPIKeyService:
    """Tests for APIKeyService class."""

    @pytest.fixture
    def api_key_service(self) -> APIKeyService:
        """Create API key service."""
        return APIKeyService(prefix="sk_test_")

    def test_generate_api_key(self, api_key_service: APIKeyService) -> None:
        """Should generate API key with prefix."""
        key = api_key_service.generate_key()

        assert key.startswith("sk_test_")
        assert len(key) > len("sk_test_")

    def test_generate_api_key_custom_length(self) -> None:
        """Should support custom key length."""
        service = APIKeyService(prefix="sk_", key_length=64)
        key = service.generate_key()

        # Key should be prefix + base64-encoded bytes
        assert key.startswith("sk_")
        assert len(key) > 64  # Prefix + encoded key

    def test_hash_api_key(self, api_key_service: APIKeyService) -> None:
        """Should hash API key for storage."""
        key = api_key_service.generate_key()
        hashed = api_key_service.hash_key(key)

        assert hashed != key
        assert isinstance(hashed, str)

    def test_hash_produces_consistent_hash(self, api_key_service: APIKeyService) -> None:
        """Should produce same hash for same key."""
        key = api_key_service.generate_key()
        hash1 = api_key_service.hash_key(key)
        hash2 = api_key_service.hash_key(key)

        assert hash1 == hash2

    def test_verify_valid_key(self, api_key_service: APIKeyService) -> None:
        """Should verify valid API key against hash."""
        key = api_key_service.generate_key()
        hashed = api_key_service.hash_key(key)

        assert api_key_service.verify_key(key, hashed) is True

    def test_verify_invalid_key(self, api_key_service: APIKeyService) -> None:
        """Should reject invalid API key."""
        key = api_key_service.generate_key()
        hashed = api_key_service.hash_key(key)

        wrong_key = api_key_service.generate_key()
        assert api_key_service.verify_key(wrong_key, hashed) is False

    def test_extract_key_id(self, api_key_service: APIKeyService) -> None:
        """Should extract key ID from API key."""
        # Generate a key with known structure
        key = api_key_service.generate_key()
        key_id = api_key_service.extract_key_id(key)

        assert isinstance(key_id, str)
        assert len(key_id) > 0

    def test_validate_key_format_valid(self, api_key_service: APIKeyService) -> None:
        """Should validate correct key format."""
        key = api_key_service.generate_key()

        assert api_key_service.validate_key_format(key) is True

    def test_validate_key_format_invalid_prefix(self, api_key_service: APIKeyService) -> None:
        """Should reject key with wrong prefix."""
        assert api_key_service.validate_key_format("wrong_prefix_abc123") is False

    def test_validate_key_format_too_short(self, api_key_service: APIKeyService) -> None:
        """Should reject key that is too short."""
        assert api_key_service.validate_key_format("sk_test_x") is False


class TestInvalidAPIKeyError:
    """Tests for InvalidAPIKeyError exception."""

    def test_invalid_api_key_error(self) -> None:
        """Should create invalid API key error."""
        error = InvalidAPIKeyError("Invalid API key format")

        assert str(error) == "Invalid API key format"
        assert isinstance(error, Exception)
