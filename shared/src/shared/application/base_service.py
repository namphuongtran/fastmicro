"""Base service patterns for application layer.

This module provides abstract base services that encapsulate common
patterns for CQRS-light architecture:

- BaseService: Foundation with caching and logging
- BaseReadService: Query operations with automatic caching
- BaseWriteService: Command operations with validation hooks
- CRUDService: Combined CRUD operations

Example:
    >>> class UserService(CRUDService[User, str]):
    ...     def __init__(self, repository: UserRepository, cache: CacheBackend):
    ...         super().__init__(repository, cache)
    ...
    ...     async def _validate_create(self, data: dict) -> None:
    ...         if await self._repository.exists_by_email(data["email"]):
    ...             raise ConflictError("Email already registered")
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from shared.cache.base import CacheBackend

# Type variables
T = TypeVar("T")  # Entity type
ID = TypeVar("ID")  # Entity ID type
CreateDTO = TypeVar("CreateDTO")
UpdateDTO = TypeVar("UpdateDTO")
ResponseDTO = TypeVar("ResponseDTO")


from shared.exceptions.base import BaseServiceException, ErrorSeverity  # noqa: E402


class ServiceError(BaseServiceException):
    """Base exception for application / service-layer errors.

    Extends :class:`BaseServiceException` so that the FastAPI exception
    handler middleware can translate these into structured JSON responses
    automatically.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=code or "SERVICE_ERROR",
            details=details,
            severity=ErrorSeverity.ERROR,
        )
        # Keep backward-compatible attributes
        self.code = code or "SERVICE_ERROR"


class NotFoundError(ServiceError):
    """Raised when an entity is not found."""

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message=message or f"{entity_type} with id '{entity_id}' not found",
            code="NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ValidationError(ServiceError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "errors": errors or []},
        )
        self.field = field
        self.errors = errors or []


class ConflictError(ServiceError):
    """Raised when there's a conflict (e.g., duplicate)."""

    def __init__(
        self,
        message: str,
        conflicting_field: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            details={"conflicting_field": conflicting_field},
        )
        self.conflicting_field = conflicting_field


@dataclass
class ServiceContext:
    """Context for service operations.

    Carries cross-cutting concerns like user identity, tenant,
    correlation IDs, etc.

    Example:
        >>> ctx = ServiceContext(
        ...     user_id="user-123",
        ...     tenant_id="tenant-456",
        ...     correlation_id="req-789",
        ... )
        >>> await service.create(data, context=ctx)
    """

    user_id: str | None = None
    tenant_id: str | None = None
    correlation_id: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        """Check if context has authenticated user."""
        return self.user_id is not None

    def has_role(self, role: str) -> bool:
        """Check if context has specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if context has specific permission."""
        return permission in self.permissions


class BaseService(ABC, Generic[T, ID]):
    """Base service with common functionality.

    Provides:
    - Logging setup
    - Optional caching support
    - Context handling

    Args:
        cache: Optional cache backend for caching operations
        cache_prefix: Prefix for cache keys
        cache_ttl: Default TTL for cached items in seconds
    """

    def __init__(
        self,
        *,
        cache: CacheBackend | None = None,
        cache_prefix: str = "",
        cache_ttl: int = 300,
    ) -> None:
        self._cache = cache
        self._cache_prefix = cache_prefix
        self._cache_ttl = cache_ttl
        self._logger = logging.getLogger(self.__class__.__name__)

    def _cache_key(self, *parts: str) -> str:
        """Generate cache key from parts."""
        all_parts = [self._cache_prefix, *parts]
        return ":".join(filter(None, all_parts))

    async def _get_cached(self, key: str) -> T | None:
        """Get item from cache."""
        if self._cache is None:
            return None
        return await self._cache.get(key)

    async def _set_cached(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set item in cache."""
        if self._cache is None:
            return
        await self._cache.set(key, value, ttl=ttl or self._cache_ttl)

    async def _delete_cached(self, key: str) -> None:
        """Delete item from cache."""
        if self._cache is None:
            return
        await self._cache.delete(key)

    async def _invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache keys matching pattern."""
        if self._cache is None:
            return
        # Note: This requires cache backend to support pattern deletion
        if hasattr(self._cache, "delete_pattern"):
            await self._cache.delete_pattern(pattern)


class BaseReadService(BaseService[T, ID]):
    """Base service for read operations.

    Provides standard query operations with automatic caching.
    Override _entity_to_response to transform entities to DTOs.

    Example:
        >>> class UserReadService(BaseReadService[User, str]):
        ...     def __init__(self, repo: UserRepository, cache: CacheBackend):
        ...         super().__init__(cache=cache, cache_prefix="user")
        ...         self._repository = repo
        ...
        ...     async def get_by_id(self, id: str) -> UserResponse | None:
        ...         # Check cache first
        ...         cached = await self._get_cached(self._cache_key(id))
        ...         if cached:
        ...             return cached
        ...         # Load from repository
        ...         user = await self._repository.get(id)
        ...         if user:
        ...             await self._set_cached(self._cache_key(id), user)
        ...         return user
    """

    @abstractmethod
    async def get_by_id(self, id: ID, *, context: ServiceContext | None = None) -> T | None:
        """Get entity by ID.

        Args:
            id: Entity identifier
            context: Service context

        Returns:
            Entity if found, None otherwise
        """
        ...

    async def get_by_id_or_raise(
        self,
        id: ID,
        entity_type: str = "Entity",
        *,
        context: ServiceContext | None = None,
    ) -> T:
        """Get entity by ID or raise NotFoundError.

        Args:
            id: Entity identifier
            entity_type: Type name for error message
            context: Service context

        Returns:
            Entity

        Raises:
            NotFoundError: If entity not found
        """
        entity = await self.get_by_id(id, context=context)
        if entity is None:
            raise NotFoundError(entity_type, id)
        return entity

    async def exists(self, id: ID, *, context: ServiceContext | None = None) -> bool:
        """Check if entity exists.

        Args:
            id: Entity identifier
            context: Service context

        Returns:
            True if entity exists
        """
        return await self.get_by_id(id, context=context) is not None


class BaseWriteService(BaseService[T, ID]):
    """Base service for write operations.

    Provides standard command operations with validation hooks.
    Override _validate_* methods for custom validation.

    Example:
        >>> class UserWriteService(BaseWriteService[User, str]):
        ...     async def _validate_create(self, data: dict) -> None:
        ...         if not data.get("email"):
        ...             raise ValidationError("Email is required", field="email")
    """

    async def _validate_create(
        self, data: dict[str, Any], *, context: ServiceContext | None = None
    ) -> None:
        """Validate data before create.

        Override to add custom validation logic.

        Args:
            data: Creation data
            context: Service context

        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _validate_update(
        self,
        id: ID,
        data: dict[str, Any],
        *,
        context: ServiceContext | None = None,
    ) -> None:
        """Validate data before update.

        Override to add custom validation logic.

        Args:
            id: Entity identifier
            data: Update data
            context: Service context

        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _validate_delete(self, id: ID, *, context: ServiceContext | None = None) -> None:
        """Validate before delete.

        Override to add custom validation logic.

        Args:
            id: Entity identifier
            context: Service context

        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _before_create(
        self, data: dict[str, Any], *, context: ServiceContext | None = None
    ) -> dict[str, Any]:
        """Hook called before create.

        Override to transform or enrich data.

        Args:
            data: Creation data
            context: Service context

        Returns:
            Transformed data
        """
        return data

    async def _after_create(self, entity: T, *, context: ServiceContext | None = None) -> None:
        """Hook called after create.

        Override to perform side effects (events, notifications, etc).

        Args:
            entity: Created entity
            context: Service context
        """
        pass

    async def _before_update(
        self,
        entity: T,
        data: dict[str, Any],
        *,
        context: ServiceContext | None = None,
    ) -> dict[str, Any]:
        """Hook called before update.

        Override to transform or enrich data.

        Args:
            entity: Current entity
            data: Update data
            context: Service context

        Returns:
            Transformed data
        """
        return data

    async def _after_update(self, entity: T, *, context: ServiceContext | None = None) -> None:
        """Hook called after update.

        Override to perform side effects.

        Args:
            entity: Updated entity
            context: Service context
        """
        pass

    async def _after_delete(self, id: ID, *, context: ServiceContext | None = None) -> None:
        """Hook called after delete.

        Override to perform side effects.

        Args:
            id: Deleted entity ID
            context: Service context
        """
        pass


class CRUDService(BaseReadService[T, ID], BaseWriteService[T, ID]):
    """Combined CRUD service.

    Provides full CRUD operations combining read and write services.

    Example:
        >>> class ProductService(CRUDService[Product, str]):
        ...     def __init__(self, repo: ProductRepository, cache: CacheBackend):
        ...         super().__init__(cache=cache, cache_prefix="product")
        ...         self._repository = repo
        ...
        ...     async def get_by_id(self, id: str) -> Product | None:
        ...         return await self._repository.get(id)
        ...
        ...     async def create(self, data: CreateProductDTO) -> Product:
        ...         await self._validate_create(data.model_dump())
        ...         product = Product(**data.model_dump())
        ...         return await self._repository.add(product)
    """

    @abstractmethod
    async def create(
        self,
        data: CreateDTO,
        *,
        context: ServiceContext | None = None,
    ) -> T:
        """Create a new entity.

        Args:
            data: Creation DTO
            context: Service context

        Returns:
            Created entity
        """
        ...

    @abstractmethod
    async def update(
        self,
        id: ID,
        data: UpdateDTO,
        *,
        context: ServiceContext | None = None,
    ) -> T:
        """Update an existing entity.

        Args:
            id: Entity identifier
            data: Update DTO
            context: Service context

        Returns:
            Updated entity

        Raises:
            NotFoundError: If entity not found
        """
        ...

    @abstractmethod
    async def delete(
        self,
        id: ID,
        *,
        context: ServiceContext | None = None,
    ) -> bool:
        """Delete an entity.

        Args:
            id: Entity identifier
            context: Service context

        Returns:
            True if deleted, False if not found
        """
        ...

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        filters: list[Any] | None = None,
        order_by: list[Any] | None = None,
        context: ServiceContext | None = None,
    ) -> PageResponse[T]:
        """List entities with pagination, filtering and ordering.

        Default implementation delegates to the repository's
        ``find_paginated`` (InMemoryRepository) or ``paginate``
        (AsyncCRUDRepository).  Override for custom behaviour.

        Args:
            page: Page number (1-based).
            size: Items per page.
            filters: Optional list of ``Filter`` instances.
            order_by: Optional list of ``OrderBy`` instances.
            context: Service context.

        Returns:
            Paginated response containing items and metadata.
        """
        from shared.dbs.repository import PageRequest

        repo = self._repository  # type: ignore[attr-defined]
        page_request = PageRequest(page=page, size=size)

        # Support both InMemoryRepository.find_paginated and
        # AsyncCRUDRepository.paginate
        if hasattr(repo, "paginate"):
            return await repo.paginate(page_request, filters=filters, order_by=order_by)
        if hasattr(repo, "find_paginated"):
            return await repo.find_paginated(page_request, filters=filters, order_by=order_by)

        # Fallback: manual pagination from get_all
        all_items = await repo.get_all()
        start = page_request.offset
        end = start + size
        return PageResponse(
            items=all_items[start:end],
            total=len(all_items),
            page=page,
            size=size,
        )

    async def search(
        self,
        *,
        filters: list[Any] | None = None,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        context: ServiceContext | None = None,
    ) -> list[T]:
        """Search entities without pagination.

        Args:
            filters: Optional list of ``Filter`` instances.
            order_by: Optional list of ``OrderBy`` instances.
            limit: Maximum number of results.
            context: Service context.

        Returns:
            List of matching entities.
        """
        repo = self._repository  # type: ignore[attr-defined]

        # AsyncCRUDRepository
        if hasattr(repo, "find_with_filters"):
            return await repo.find_with_filters(
                filters=filters,
                order_by=order_by,
                limit=limit,
            )
        # InMemoryRepository
        if hasattr(repo, "find"):
            results = await repo.find(filters=filters, order_by=order_by)
            if limit is not None:
                return results[:limit]
            return results

        # Fallback
        return await repo.get_all()


# ---------------------------------------------------------------------------
# PaginatedResult — thin backward-compatible alias for PageResponse
# ---------------------------------------------------------------------------
# ``PageResponse`` in ``shared.dbs.repository`` is the canonical paginated
# container.  ``PaginatedResult`` is kept as an alias so existing service
# code that imports it from ``shared.application`` keeps working.
#
# New code should import ``PageResponse`` directly from shared.dbs.
# ---------------------------------------------------------------------------
from shared.dbs.repository import PageResponse  # noqa: E402

PaginatedResult = PageResponse
