"""Consent repository interface - defines data access for user consents."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity_service.domain.entities import Consent, Session


class ConsentRepository(ABC):
    """Abstract repository for Consent aggregate persistence."""

    @abstractmethod
    async def get_by_id(self, consent_id: uuid.UUID) -> Consent | None:
        """Get consent by ID.

        Args:
            consent_id: Consent UUID

        Returns:
            Consent if found, None otherwise.
        """

    @abstractmethod
    async def get_by_user_and_client(
        self, user_id: uuid.UUID, client_id: str
    ) -> Consent | None:
        """Get consent for a specific user-client pair.

        Args:
            user_id: User's UUID
            client_id: OAuth2 client_id

        Returns:
            Consent if found, None otherwise.
        """

    @abstractmethod
    async def save(self, consent: Consent) -> Consent:
        """Save or update a consent.

        Args:
            consent: Consent to save

        Returns:
            Saved consent.
        """

    @abstractmethod
    async def delete(self, consent_id: uuid.UUID) -> bool:
        """Delete a consent.

        Args:
            consent_id: Consent UUID

        Returns:
            True if consent was deleted.
        """

    @abstractmethod
    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        """Delete all consents for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of consents deleted.
        """

    @abstractmethod
    async def delete_for_client(self, client_id: str) -> int:
        """Delete all consents for a client.

        Args:
            client_id: OAuth2 client_id

        Returns:
            Number of consents deleted.
        """

    @abstractmethod
    async def list_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Consent]:
        """List all consents for a user.

        Args:
            user_id: User's UUID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of consents.
        """


class SessionRepository(ABC):
    """Abstract repository for user session storage.

    Sessions are stored in Redis for fast lookup.
    """

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save a session.

        Args:
            session: Session to save
        """

    @abstractmethod
    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        """Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session if found and valid, None otherwise.
        """

    @abstractmethod
    async def delete(self, session_id: uuid.UUID) -> bool:
        """Delete a session.

        Args:
            session_id: Session UUID

        Returns:
            True if session was deleted.
        """

    @abstractmethod
    async def delete_all_for_user(self, user_id: uuid.UUID) -> int:
        """Delete all sessions for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of sessions deleted.
        """

    @abstractmethod
    async def list_by_user(self, user_id: uuid.UUID) -> list[Session]:
        """List all active sessions for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of active sessions.
        """

    @abstractmethod
    async def update_activity(self, session_id: uuid.UUID) -> bool:
        """Update session last activity timestamp.

        Args:
            session_id: Session UUID

        Returns:
            True if session was updated.
        """

    @abstractmethod
    async def extend(self, session_id: uuid.UUID, seconds: int) -> bool:
        """Extend session expiration.

        Args:
            session_id: Session UUID
            seconds: Seconds to extend by

        Returns:
            True if session was extended.
        """
