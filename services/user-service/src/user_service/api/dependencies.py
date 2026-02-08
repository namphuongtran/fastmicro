"""FastAPI dependencies for dependency injection.

Defines reusable Annotated type aliases following FastAPI best practices.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from shared.application.base_service import ServiceContext
from shared.ddd.events import EventDispatcher
from shared.fastapi_utils.dependencies import get_service_context

from user_service.application.services.user_service import UserApplicationService
from user_service.configs.settings import UserServiceSettings, get_settings
from user_service.domain.repositories import UserRepository

# =============================================================================
# Settings
# =============================================================================
SettingsDep = Annotated[UserServiceSettings, Depends(get_settings)]
ServiceContextDep = Annotated[ServiceContext, Depends(get_service_context)]

# =============================================================================
# Singletons (set during lifespan)
# =============================================================================
_user_repository: UserRepository | None = None
_event_dispatcher: EventDispatcher | None = None


def set_repository(repo: UserRepository) -> None:
    """Wire repository at startup (called from lifespan)."""
    global _user_repository  # noqa: PLW0603
    _user_repository = repo


def set_event_dispatcher(dispatcher: EventDispatcher) -> None:
    """Wire event dispatcher at startup (called from lifespan)."""
    global _event_dispatcher  # noqa: PLW0603
    _event_dispatcher = dispatcher


def get_user_repository() -> UserRepository:
    """Provide the UserRepository instance."""
    if _user_repository is None:
        msg = "UserRepository not initialised — call set_repository() in lifespan"
        raise RuntimeError(msg)
    return _user_repository


def get_user_service() -> UserApplicationService:
    """Provide the UserApplicationService instance."""
    return UserApplicationService(
        repository=get_user_repository(),
        event_dispatcher=_event_dispatcher,
    )


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserServiceDep = Annotated[UserApplicationService, Depends(get_user_service)]
