"""FastAPI dependencies for Identity Admin Service.

Provides dependency injection for repositories and services.
Uses shared domain entities and repositories from identity-service
via database connection to the shared PostgreSQL database.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from identity_admin_service.configs import Settings, get_settings

# =============================================================================
# Annotated Type Aliases for Dependency Injection
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]


# =============================================================================
# In-Memory Repositories (Development/Testing)
# =============================================================================
# These mirror the identity-service repositories for admin operations.
# In production, these would connect to the shared PostgreSQL database.


class InMemoryUserRepository:
    """In-memory user repository for development/testing."""

    def __init__(self) -> None:
        """Initialize the in-memory storage."""
        self._users: dict[str, any] = {}  # Keyed by UUID

    async def get_by_id(self, user_id):
        """Get user by internal UUID."""
        return self._users.get(str(user_id))

    async def get_by_email(self, email: str):
        """Get user by email address."""
        for user in self._users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_username(self, username: str):
        """Get user by username."""
        for user in self._users.values():
            if user.username and user.username.lower() == username.lower():
                return user
        return None

    async def create(self, user):
        """Create a new user."""
        self._users[str(user.id)] = user
        return user

    async def update(self, user):
        """Update an existing user."""
        self._users[str(user.id)] = user
        return user

    async def delete(self, user_id):
        """Delete (deactivate) a user."""
        user = self._users.get(str(user_id))
        if user:
            user.is_active = False
            return True
        return False

    async def count(self, include_inactive: bool = False) -> int:
        """Count total users."""
        if include_inactive:
            return len(self._users)
        return len([u for u in self._users.values() if u.is_active])

    async def search(self, query: str, skip: int = 0, limit: int = 100, include_inactive: bool = False):
        """Search users by email or username."""
        query_lower = query.lower()
        results = []
        for user in self._users.values():
            if not include_inactive and not user.is_active:
                continue
            if not query or query_lower in user.email.lower() or (user.username and query_lower in user.username.lower()):
                results.append(user)
        return results[skip : skip + limit]

    async def find_by_role(self, role_name: str):
        """Find users with a specific role."""
        results = []
        for user in self._users.values():
            if any(r.role_name == role_name for r in user.roles if r.is_active()):
                results.append(user)
        return results


class InMemoryClientRepository:
    """In-memory client repository for development/testing."""

    def __init__(self) -> None:
        """Initialize the in-memory storage."""
        self._clients: dict[str, any] = {}  # Keyed by client_id (OAuth2 public identifier)
        self._clients_by_uuid: dict[str, any] = {}  # Keyed by internal UUID

    async def get_by_id(self, client_id):
        """Get client by internal UUID."""
        return self._clients_by_uuid.get(str(client_id))

    async def get_by_client_id(self, client_id: str):
        """Get client by OAuth2 client_id (public identifier)."""
        return self._clients.get(client_id)

    async def create(self, client):
        """Create a new client."""
        self._clients[client.client_id] = client
        self._clients_by_uuid[str(client.id)] = client
        return client

    async def update(self, client):
        """Update an existing client."""
        self._clients[client.client_id] = client
        self._clients_by_uuid[str(client.id)] = client
        return client

    async def delete(self, client_id):
        """Delete (deactivate) a client."""
        client = self._clients_by_uuid.get(str(client_id))
        if client:
            client.is_active = False
            return True
        return False

    async def list_active(self, skip: int = 0, limit: int = 100):
        """List all active clients."""
        active = [c for c in self._clients.values() if c.is_active]
        return active[skip : skip + limit]

    async def count(self, include_inactive: bool = False) -> int:
        """Count total clients."""
        if include_inactive:
            return len(self._clients)
        return len([c for c in self._clients.values() if c.is_active])

    async def search(self, query: str, skip: int = 0, limit: int = 100, include_inactive: bool = False):
        """Search clients by name or client_id."""
        query_lower = query.lower()
        results = []
        for client in self._clients.values():
            if not include_inactive and not client.is_active:
                continue
            if not query or query_lower in client.client_id.lower() or query_lower in client.client_name.lower():
                results.append(client)
        return results[skip : skip + limit]


# Singleton instances
_user_repo = InMemoryUserRepository()
_client_repo = InMemoryClientRepository()


def get_client_repository() -> InMemoryClientRepository:
    """Get the client repository singleton.

    Returns:
        Client repository instance for OAuth2 client management.
    """
    return _client_repo


def get_user_repository() -> InMemoryUserRepository:
    """Get the user repository singleton.

    Returns:
        User repository instance for user management.
    """
    return _user_repo
