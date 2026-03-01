"""FastAPI dependencies for dependency injection.

Defines reusable Annotated type aliases following FastAPI best practices.
Uses PostgreSQL repositories (via shared.identity) for persistent storage
and in-memory repositories for Redis-backed entities (auth codes, sessions,
token blacklist).

See: https://fastapi.tiangolo.com/tutorial/dependencies/
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.application.services import MFAService, OAuth2Service, UserAuthService
from identity_service.configs import Settings, get_settings
from identity_service.infrastructure.database import get_db_session

# PostgreSQL-backed repositories from shared library
from shared.identity.repositories import (
    ClientRepository,
    ConsentRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)

# =============================================================================
# Annotated Type Aliases for Dependency Injection
# =============================================================================
# These provide clean, reusable type annotations that can be imported and used
# in route handlers. Example:
#   async def endpoint(service: OAuth2ServiceDep) -> Response:
#       ...

# Settings dependency - cached singleton
SettingsDep = Annotated[Settings, Depends(get_settings)]


# =============================================================================
# In-Memory Repositories (Redis-backed entities - kept until Redis implementation)
# =============================================================================
# These entities (auth codes, token blacklist, sessions) are designed for
# Redis storage. Using in-memory stubs until Redis implementation.
# NOTE: In multi-worker deployments, each worker has its own instance.
# =============================================================================


class InMemoryAuthCodeRepository:
    """In-memory auth code repository."""

    def __init__(self):
        self._codes = {}

    async def save(self, code):
        self._codes[code.code] = code

    async def get_by_code(self, code):
        return self._codes.get(code)

    async def delete(self, code):
        if code in self._codes:
            del self._codes[code]
            return True
        return False

    async def mark_as_used(self, code):
        if code in self._codes:
            self._codes[code].is_used = True
            return True
        return False


class InMemoryTokenBlacklistRepository:
    """In-memory token blacklist repository."""

    def __init__(self):
        self._blacklist = {}

    async def add(self, entry):
        self._blacklist[entry.jti] = entry

    async def is_blacklisted(self, jti):
        return jti in self._blacklist

    async def remove(self, jti):
        if jti in self._blacklist:
            del self._blacklist[jti]
            return True
        return False


class InMemorySessionRepository:
    """In-memory session repository."""

    def __init__(self):
        self._sessions = {}

    async def save(self, session):
        self._sessions[str(session.id)] = session

    async def get_by_id(self, session_id):
        return self._sessions.get(str(session_id))

    async def delete(self, session_id):
        key = str(session_id)
        if key in self._sessions:
            del self._sessions[key]
            return True
        return False

    async def delete_all_for_user(self, user_id):
        count = 0
        for k, v in list(self._sessions.items()):
            if v.user_id == user_id:
                del self._sessions[k]
                count += 1
        return count

    async def list_by_user(self, user_id):
        return [v for v in self._sessions.values() if v.user_id == user_id and v.is_valid()]

    async def update_activity(self, session_id):
        session = await self.get_by_id(session_id)
        if session:
            session.update_activity()
            return True
        return False

    async def extend(self, session_id, seconds):
        from datetime import timedelta

        session = await self.get_by_id(session_id)
        if session and session.expires_at:
            session.expires_at += timedelta(seconds=seconds)
            return True
        return False


# =============================================================================
# Database Session Dependency
# =============================================================================

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# =============================================================================
# PostgreSQL Repository Dependencies (session-scoped)
# =============================================================================


def get_user_repository(session: DbSessionDep) -> UserRepository:
    """Get session-scoped PostgreSQL user repository."""
    return UserRepository(session)


def get_client_repository(session: DbSessionDep) -> ClientRepository:
    """Get session-scoped PostgreSQL client repository."""
    return ClientRepository(session)


def get_refresh_token_repository(session: DbSessionDep) -> RefreshTokenRepository:
    """Get session-scoped PostgreSQL refresh token repository."""
    return RefreshTokenRepository(session)


def get_consent_repository(session: DbSessionDep) -> ConsentRepository:
    """Get session-scoped PostgreSQL consent repository."""
    return ConsentRepository(session)


def get_password_reset_repository(session: DbSessionDep) -> PasswordResetRepository:
    """Get session-scoped PostgreSQL password reset repository."""
    return PasswordResetRepository(session)


# Annotated type aliases for repositories
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
ClientRepoDep = Annotated[ClientRepository, Depends(get_client_repository)]
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]
ConsentRepoDep = Annotated[ConsentRepository, Depends(get_consent_repository)]
PasswordResetRepoDep = Annotated[PasswordResetRepository, Depends(get_password_reset_repository)]


# =============================================================================
# In-Memory Repositories (Redis-backed entities - kept until Redis implementation)
# =============================================================================

# Singleton instances for Redis-only repositories
_auth_code_repo = InMemoryAuthCodeRepository()
_blacklist_repo = InMemoryTokenBlacklistRepository()
_session_repo = InMemorySessionRepository()


async def get_oauth2_service(
    settings: SettingsDep,
    user_repository: UserRepoDep,
    client_repository: ClientRepoDep,
    refresh_token_repository: RefreshTokenRepoDep,
    consent_repository: ConsentRepoDep,
) -> OAuth2Service:
    """Get OAuth2 service instance with PostgreSQL-backed repositories.

    Args:
        settings: Application settings
        user_repository: PostgreSQL user repository
        client_repository: PostgreSQL client repository
        refresh_token_repository: PostgreSQL refresh token repository
        consent_repository: PostgreSQL consent repository

    Returns:
        OAuth2Service instance.
    """
    from identity_service.infrastructure.security import (
        get_jwt_service,
        get_password_service,
    )

    return OAuth2Service(
        settings=settings,
        jwt_service=get_jwt_service(settings),
        password_service=get_password_service(settings),
        user_repository=user_repository,
        client_repository=client_repository,
        auth_code_repository=_auth_code_repo,
        refresh_token_repository=refresh_token_repository,
        token_blacklist_repository=_blacklist_repo,
        consent_repository=consent_repository,
        session_repository=_session_repo,
    )


# OAuth2 service dependency - primary service for authentication/authorization
OAuth2ServiceDep = Annotated[OAuth2Service, Depends(get_oauth2_service)]


# =============================================================================
# Auth Services
# =============================================================================


async def get_user_auth_service(
    settings: SettingsDep,
    user_repository: UserRepoDep,
    password_reset_repository: PasswordResetRepoDep,
) -> UserAuthService:
    """Get UserAuthService instance with PostgreSQL-backed repositories.

    Returns:
        UserAuthService for registration, login, and password operations.
    """
    from identity_service.infrastructure.security import (
        get_brute_force_protection_service,
        get_jwt_service,
        get_password_policy_service,
        get_password_service,
        get_session_management_service,
    )

    return UserAuthService(
        settings=settings,
        user_repository=user_repository,
        password_reset_repository=password_reset_repository,
        password_service=get_password_service(settings),
        password_policy_service=get_password_policy_service(settings),
        brute_force_service=get_brute_force_protection_service(settings),
        session_service=get_session_management_service(),
        jwt_service=get_jwt_service(settings),
    )


async def get_mfa_service(
    settings: SettingsDep,
    user_repository: UserRepoDep,
) -> MFAService:
    """Get MFAService instance with PostgreSQL-backed user repository.

    Returns:
        MFAService for TOTP setup, verification, and recovery.
    """
    from identity_service.infrastructure.security import (
        get_jwt_service,
        get_password_service,
    )

    return MFAService(
        settings=settings,
        user_repository=user_repository,
        password_service=get_password_service(settings),
        jwt_service=get_jwt_service(settings),
    )


# Annotated type aliases for auth services
UserAuthServiceDep = Annotated[UserAuthService, Depends(get_user_auth_service)]
MFAServiceDep = Annotated[MFAService, Depends(get_mfa_service)]


# =============================================================================
# Current User (JWT-based authentication)
# =============================================================================


async def get_current_user_id(
    settings: SettingsDep,
) -> uuid.UUID:
    """Extract user ID from JWT bearer token.

    This is a simplified stub that returns a placeholder UUID.
    In production, this would extract and validate the JWT from
    the Authorization header.

    Returns:
        Authenticated user's UUID.

    Raises:
        HTTPException: If not authenticated.
    """
    # TODO: Replace with actual JWT extraction from Authorization header
    # For now, a placeholder to allow compilation
    from fastapi import HTTPException

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
