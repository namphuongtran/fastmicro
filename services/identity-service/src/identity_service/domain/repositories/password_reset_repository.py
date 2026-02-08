"""Password reset token repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity_service.domain.entities.password_reset import PasswordResetToken


class PasswordResetRepository(ABC):
    """Abstract repository for password reset token persistence.

    Tokens are short-lived and typically stored in Redis.
    """

    @abstractmethod
    async def save(self, token: PasswordResetToken) -> None:
        """Save a password reset token.

        Args:
            token: Password reset token to save.
        """

    @abstractmethod
    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Get reset token by its value.

        Args:
            token: The reset token string.

        Returns:
            PasswordResetToken if found, None otherwise.
        """

    @abstractmethod
    async def mark_as_used(self, token: str) -> bool:
        """Mark a token as used (consumed).

        Args:
            token: The reset token string.

        Returns:
            True if token was marked as used.
        """

    @abstractmethod
    async def delete_expired(self) -> int:
        """Delete all expired tokens.

        Returns:
            Number of tokens deleted.
        """

    @abstractmethod
    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        """Delete all reset tokens for a user (e.g., after successful reset).

        Args:
            user_id: User's UUID.

        Returns:
            Number of tokens deleted.
        """
