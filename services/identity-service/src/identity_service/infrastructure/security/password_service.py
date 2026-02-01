"""Password hashing service using Argon2 (with bcrypt fallback for migration)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings


class PasswordService:
    """Password hashing and verification service.

    Uses Argon2 for new hashes with bcrypt fallback for existing passwords.
    This allows gradual migration from bcrypt to Argon2.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize password service.

        Args:
            settings: Application settings
        """
        self._settings = settings
        # Argon2 first = new hashes use Argon2 (more secure)
        # Bcrypt second = can still verify existing bcrypt hashes
        self._hasher = PasswordHash(
            (
                Argon2Hasher(),
                BcryptHasher(rounds=settings.bcrypt_rounds),
            )
        )

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2.

        Args:
            password: Plain text password

        Returns:
            Hashed password string.
        """
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Supports both Argon2 and bcrypt hashes for backward compatibility.

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash

        Returns:
            True if password matches.
        """
        return self._hasher.verify(password, password_hash)

    def verify_and_update(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        """Verify password and upgrade hash if needed.

        If password is valid and hash uses outdated algorithm (bcrypt)
        or outdated parameters, returns new hash for database update.

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash

        Returns:
            Tuple of (is_valid, new_hash_or_none).
            new_hash is only set if hash needs upgrade.
        """
        return self._hasher.verify_and_update(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if password hash needs to be updated.

        Returns True if hash uses bcrypt (should upgrade to Argon2)
        or if Argon2 parameters have changed.

        Args:
            password_hash: Stored password hash

        Returns:
            True if hash should be updated.
        """
        # Argon2 hashes start with $argon2, bcrypt with $2
        return not password_hash.startswith("$argon2")

    def validate_password(self, password: str) -> list[str]:
        """Validate password against policy.

        Args:
            password: Password to validate

        Returns:
            List of validation errors (empty if valid).
        """
        import re

        errors: list[str] = []
        settings = self._settings

        if len(password) < settings.password_min_length:
            errors.append(f"Password must be at least {settings.password_min_length} characters")

        if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if settings.password_require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if settings.password_require_digit and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if settings.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        return errors


_password_service: PasswordService | None = None


def get_password_service(settings: Settings) -> PasswordService:
    """Get password service instance."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService(settings)
    return _password_service
