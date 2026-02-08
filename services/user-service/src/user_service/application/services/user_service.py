"""User application service — orchestrates use cases."""

from __future__ import annotations

from uuid import uuid4

import structlog
from shared.application.base_service import (
    ConflictError,
    NotFoundError,
    ServiceContext,
)
from shared.ddd.events import EventDispatcher

from user_service.application.dtos import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from user_service.domain.entities.user import User
from user_service.domain.repositories import UserRepository

logger = structlog.get_logger()


class UserApplicationService:
    """Application service for User aggregate operations.

    Orchestrates use cases bridging the API and domain layers.
    Handles validation, persistence, and event dispatching.
    """

    def __init__(
        self,
        repository: UserRepository,
        event_dispatcher: EventDispatcher | None = None,
    ) -> None:
        self._repository = repository
        self._event_dispatcher = event_dispatcher

    async def create_user(
        self,
        dto: CreateUserRequest,
        *,
        context: ServiceContext | None = None,
    ) -> UserResponse:
        """Create a new user.

        Args:
            dto: Creation request data.
            context: Service context with caller information.

        Returns:
            Created user response.

        Raises:
            ConflictError: If email already registered.
        """
        # Uniqueness check
        if await self._repository.exists_by_email(dto.email):
            raise ConflictError(
                f"Email '{dto.email}' is already registered",
                conflicting_field="email",
            )

        tenant_id = dto.tenant_id
        if tenant_id is None and context and context.tenant_id:
            tenant_id = context.tenant_id

        user = User.create(
            id=str(uuid4()),
            email=dto.email,
            display_name=dto.display_name,
            first_name=dto.first_name,
            last_name=dto.last_name,
            tenant_id=tenant_id or "",
        )

        await self._repository.add(user)
        await self._dispatch_events(user)

        logger.info(
            "user_created",
            user_id=str(user.id),
            email=dto.email,
            tenant_id=tenant_id,
        )
        return self._to_response(user)

    async def get_user(
        self,
        user_id: str,
        *,
        context: ServiceContext | None = None,
    ) -> UserResponse:
        """Get a user by ID.

        Args:
            user_id: Unique user identifier.
            context: Service context.

        Returns:
            User response.

        Raises:
            NotFoundError: If user not found.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return self._to_response(user)

    async def update_user(
        self,
        user_id: str,
        dto: UpdateUserRequest,
        *,
        context: ServiceContext | None = None,
    ) -> UserResponse:
        """Update an existing user.

        Args:
            user_id: Unique user identifier.
            dto: Update request data.
            context: Service context.

        Returns:
            Updated user response.

        Raises:
            NotFoundError: If user not found.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)

        changes: dict[str, str] = {}
        if dto.display_name is not None:
            changes["display_name"] = dto.display_name
        if dto.first_name is not None:
            changes["first_name"] = dto.first_name
        if dto.last_name is not None:
            changes["last_name"] = dto.last_name

        if changes:
            user.update_profile(**changes)
            await self._repository.update(user)
            await self._dispatch_events(user)

        logger.info(
            "user_updated",
            user_id=user_id,
            changed_fields=list(changes.keys()),
        )
        return self._to_response(user)

    async def deactivate_user(
        self,
        user_id: str,
        *,
        context: ServiceContext | None = None,
    ) -> UserResponse:
        """Deactivate a user.

        Args:
            user_id: Unique user identifier.
            context: Service context.

        Returns:
            Updated user response.

        Raises:
            NotFoundError: If user not found.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)

        reason = "admin_deactivation"
        if context and context.user_id:
            reason = f"deactivated_by:{context.user_id}"
        user.deactivate(reason=reason)
        await self._repository.update(user)
        await self._dispatch_events(user)

        logger.info("user_deactivated", user_id=user_id, reason=reason)
        return self._to_response(user)

    async def delete_user(
        self,
        user_id: str,
        *,
        context: ServiceContext | None = None,
    ) -> None:
        """Delete a user.

        Args:
            user_id: Unique user identifier.
            context: Service context.

        Raises:
            NotFoundError: If user not found.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)

        await self._repository.delete(user_id)
        logger.info("user_deleted", user_id=user_id)

    async def list_users(
        self,
        *,
        tenant_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        context: ServiceContext | None = None,
    ) -> UserListResponse:
        """List users with pagination.

        Args:
            tenant_id: Filter by tenant (falls back to context tenant).
            offset: Pagination offset.
            limit: Page size.
            context: Service context.

        Returns:
            Paginated user list response.
        """
        effective_tenant = tenant_id
        if effective_tenant is None and context and context.tenant_id:
            effective_tenant = context.tenant_id

        users = await self._repository.list_by_tenant(
            tenant_id=effective_tenant or "",
            offset=offset,
            limit=limit,
        )
        return UserListResponse(
            items=[self._to_response(u) for u in users],
            total=len(users),  # placeholder until count query
            offset=offset,
            limit=limit,
        )

    # ---- internal helpers ----

    async def _dispatch_events(self, user: User) -> None:
        """Dispatch collected domain events."""
        if self._event_dispatcher is None:
            return
        for event in user.clear_events():
            await self._event_dispatcher.dispatch(event)

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        """Map User aggregate to response DTO."""
        return UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
