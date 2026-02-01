"""Token repository interface - defines data access contract for tokens."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity_service.domain.entities import (
        AuthorizationCode,
        RefreshToken,
        TokenBlacklistEntry,
    )


class AuthorizationCodeRepository(ABC):
    """Abstract repository for authorization code storage.

    Authorization codes are short-lived and typically stored in Redis.
    """

    @abstractmethod
    async def save(self, code: AuthorizationCode) -> None:
        """Save an authorization code.

        Args:
            code: Authorization code to save
        """

    @abstractmethod
    async def get_by_code(self, code: str) -> AuthorizationCode | None:
        """Get authorization code by its value.

        Args:
            code: The authorization code string

        Returns:
            AuthorizationCode if found and not expired, None otherwise.
        """

    @abstractmethod
    async def delete(self, code: str) -> bool:
        """Delete an authorization code.

        Args:
            code: The authorization code string

        Returns:
            True if code was deleted.
        """

    @abstractmethod
    async def mark_as_used(self, code: str) -> bool:
        """Mark authorization code as used.

        Args:
            code: The authorization code string

        Returns:
            True if code was marked as used.
        """


class RefreshTokenRepository(ABC):
    """Abstract repository for refresh token persistence.

    Refresh tokens are long-lived and stored in the database.
    """

    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken:
        """Save a refresh token.

        Args:
            token: Refresh token to save

        Returns:
            Saved refresh token.
        """

    @abstractmethod
    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Get refresh token by its value.

        Args:
            token: The refresh token string

        Returns:
            RefreshToken if found, None otherwise.
        """

    @abstractmethod
    async def get_by_id(self, token_id: uuid.UUID) -> RefreshToken | None:
        """Get refresh token by ID.

        Args:
            token_id: The refresh token UUID

        Returns:
            RefreshToken if found, None otherwise.
        """

    @abstractmethod
    async def revoke(self, token: str, replaced_by: str | None = None) -> bool:
        """Revoke a refresh token.

        Args:
            token: The refresh token string
            replaced_by: Optional replacement token (for rotation)

        Returns:
            True if token was revoked.
        """

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all refresh tokens for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of tokens revoked.
        """

    @abstractmethod
    async def revoke_all_for_client(self, client_id: str) -> int:
        """Revoke all refresh tokens for a client.

        Args:
            client_id: OAuth2 client_id

        Returns:
            Number of tokens revoked.
        """

    @abstractmethod
    async def revoke_all_for_user_and_client(self, user_id: uuid.UUID, client_id: str) -> int:
        """Revoke all refresh tokens for a user-client combination.

        Args:
            user_id: User's UUID
            client_id: OAuth2 client_id

        Returns:
            Number of tokens revoked.
        """

    @abstractmethod
    async def list_active_for_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[RefreshToken]:
        """List active refresh tokens for a user.

        Args:
            user_id: User's UUID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of active refresh tokens.
        """

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired refresh tokens.

        Returns:
            Number of tokens removed.
        """


class TokenBlacklistRepository(ABC):
    """Abstract repository for token blacklist (revoked JWTs).

    The blacklist is stored in Redis with TTL matching token expiration.
    """

    @abstractmethod
    async def add(self, entry: TokenBlacklistEntry) -> None:
        """Add a token to the blacklist.

        Args:
            entry: Blacklist entry containing JTI and expiration
        """

    @abstractmethod
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token (by JTI) is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted.
        """

    @abstractmethod
    async def remove(self, jti: str) -> bool:
        """Remove a token from the blacklist.

        Args:
            jti: JWT ID to remove

        Returns:
            True if entry was removed.
        """
