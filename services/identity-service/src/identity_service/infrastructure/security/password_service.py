"""Password hashing service using bcrypt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from passlib.context import CryptContext

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings


class PasswordService:
    """Password hashing and verification service.

    Uses bcrypt with configurable work factor.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize password service.

        Args:
            settings: Application settings
        """
        self._settings = settings
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.bcrypt_rounds,
        )

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string.
        """
        return self._context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash

        Returns:
            True if password matches.
        """
        return self._context.verify(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if password hash needs to be updated.

        This is useful when changing bcrypt rounds.

        Args:
            password_hash: Stored password hash

        Returns:
            True if hash should be updated.
        """
        return self._context.needs_update(password_hash)

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
            errors.append(
                f"Password must be at least {settings.password_min_length} characters"
            )

        if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if settings.password_require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if settings.password_require_digit and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if settings.password_require_special and not re.search(
            r'[!@#$%^&*(),.?":{}|<>]', password
        ):
            errors.append("Password must contain at least one special character")

        return errors


_password_service: PasswordService | None = None


def get_password_service(settings: Settings) -> PasswordService:
    """Get password service instance."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService(settings)
    return _password_service
