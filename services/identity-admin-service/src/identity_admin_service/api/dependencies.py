"""FastAPI dependencies for Identity Admin Service.

Provides dependency injection for repositories and services.
Uses shared PostgreSQL-backed repositories from shared.identity
for persistent storage, connecting to the same database as identity-service.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from identity_admin_service.configs import Settings, get_settings
from identity_admin_service.database import get_db_session

# PostgreSQL-backed repositories from shared library
from shared.identity.repositories import (
    ClientRepository,
    UserRepository,
)

# =============================================================================
# Annotated Type Aliases for Dependency Injection
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]


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


# Annotated type aliases for repositories
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
ClientRepoDep = Annotated[ClientRepository, Depends(get_client_repository)]
