"""API key generation and validation service.

This module provides API key management for service-to-service
authentication and external API access.

Example:
    >>> from shared.auth.api_key import APIKeyService
    >>> service = APIKeyService(prefix="sk_live_")
    >>> key = service.generate_key()
    >>> hashed = service.hash_key(key)
    >>> service.verify_key(key, hashed)
    True
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any


class InvalidAPIKeyError(Exception):
    """Raised when an API key is invalid or malformed."""

    pass


@dataclass
class APIKeyData:
    """Data associated with an API key.

    Attributes:
        key_id: Unique identifier for the key (not the key itself).
        name: Human-readable name for the key.
        scopes: List of permission scopes.
        is_active: Whether the key is currently active.
        metadata: Additional metadata for the key.
    """

    key_id: str
    name: str
    scopes: list[str] = field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope.

        Args:
            scope: The scope to check.

        Returns:
            True if the key has the scope.
        """
        return scope in self.scopes


class APIKeyService:
    """Service for API key generation and validation.

    API keys are designed for:
    - Service-to-service authentication
    - External API access
    - Long-lived credentials

    Key Format: {prefix}{key_id}_{random_bytes}

    The prefix allows identification of key type/environment:
    - sk_live_ : Production secret keys
    - sk_test_ : Test/staging secret keys
    - pk_live_ : Production publishable keys

    Attributes:
        prefix: Prefix for generated keys.
        key_length: Length of random bytes (default: 32).

    Example:
        >>> service = APIKeyService(prefix="sk_test_")
        >>> key = service.generate_key()
        >>> key.startswith("sk_test_")
        True
    """

    def __init__(
        self,
        prefix: str = "sk_",
        key_length: int = 32,
    ) -> None:
        """Initialize API key service.

        Args:
            prefix: Prefix for generated keys.
            key_length: Number of random bytes for the key.
        """
        self.prefix = prefix
        self.key_length = key_length
        # Minimum key length after prefix (prefix + key_id + separator + random)
        self._min_key_length = len(prefix) + 8 + 1 + 16

    def generate_key(self) -> str:
        """Generate a new API key.

        The key format is: {prefix}{key_id}_{random_bytes}

        Returns:
            A new API key string.

        Example:
            >>> key = service.generate_key()
            >>> key.startswith(service.prefix)
            True
        """
        # Generate a short key ID (8 chars)
        key_id = secrets.token_hex(4)  # 8 hex chars

        # Generate random bytes for the key
        random_bytes = secrets.token_urlsafe(self.key_length)

        return f"{self.prefix}{key_id}_{random_bytes}"

    def hash_key(self, api_key: str) -> str:
        """Hash an API key for storage.

        Uses SHA-256 for consistent, fast hashing. API keys are
        already high-entropy, so a simple hash is sufficient
        (unlike passwords which need Argon2/bcrypt).

        Args:
            api_key: The API key to hash.

        Returns:
            SHA-256 hash of the key (hex-encoded).

        Example:
            >>> hashed = service.hash_key(key)
            >>> len(hashed) == 64  # SHA-256 hex digest
            True
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_key(self, api_key: str, hashed: str) -> bool:
        """Verify an API key against a stored hash.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            api_key: The API key to verify.
            hashed: The stored hash to compare against.

        Returns:
            True if the key matches the hash.

        Example:
            >>> key = service.generate_key()
            >>> hashed = service.hash_key(key)
            >>> service.verify_key(key, hashed)
            True
        """
        key_hash = self.hash_key(api_key)
        return secrets.compare_digest(key_hash, hashed)

    def extract_key_id(self, api_key: str) -> str:
        """Extract the key ID from an API key.

        The key ID can be used to look up metadata without
        exposing the full key.

        Args:
            api_key: The API key.

        Returns:
            The key ID portion of the key.

        Raises:
            InvalidAPIKeyError: If the key format is invalid.

        Example:
            >>> key = service.generate_key()
            >>> key_id = service.extract_key_id(key)
            >>> len(key_id) == 8
            True
        """
        if not self.validate_key_format(api_key):
            raise InvalidAPIKeyError("Invalid API key format")

        # Remove prefix and extract key_id (before the underscore)
        key_without_prefix = api_key[len(self.prefix) :]
        parts = key_without_prefix.split("_", 1)

        if len(parts) != 2:
            raise InvalidAPIKeyError("Invalid API key format")

        return parts[0]

    def validate_key_format(self, api_key: str) -> bool:
        """Validate the format of an API key.

        Checks that the key:
        - Starts with the correct prefix
        - Has the expected structure
        - Has minimum length

        Args:
            api_key: The API key to validate.

        Returns:
            True if the key format is valid.

        Example:
            >>> key = service.generate_key()
            >>> service.validate_key_format(key)
            True
            >>> service.validate_key_format("invalid")
            False
        """
        # Check prefix
        if not api_key.startswith(self.prefix):
            return False

        # Check minimum length
        if len(api_key) < self._min_key_length:
            return False

        # Check structure (should have underscore after key_id)
        key_without_prefix = api_key[len(self.prefix) :]
        return "_" in key_without_prefix


__all__ = [
    "APIKeyData",
    "APIKeyService",
    "InvalidAPIKeyError",
]
