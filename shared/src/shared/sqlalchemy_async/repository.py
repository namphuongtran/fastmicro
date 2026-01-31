"""Async SQLAlchemy repository pattern implementation.

This module provides generic async repository classes:
- AsyncRepository: Base repository interface  
- AsyncCRUDRepository: Full CRUD implementation with filtering/pagination

Integrates with shared.dbs abstract patterns for consistency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

from shared.dbs.repository import (
    AbstractRepository,
    Filter,
    FilterOperator,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)

# Type variables for generic repository
T = TypeVar("T", bound=DeclarativeBase)  # Entity type
ID = TypeVar("ID")  # Primary key type


class AsyncRepository(ABC, Generic[T, ID]):
    """Abstract base class for async repositories.
    
    Provides interface for data access operations.
    
    Type Parameters:
        T: Entity/model type (must extend DeclarativeBase).
        ID: Primary key type.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.
        
        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Get current session."""
        return self._session

    @property
    @abstractmethod
    def model_class(self) -> type[T]:
        """Get the model class for this repository."""
        ...

    @abstractmethod
    async def get_by_id(self, id: ID) -> T | None:
        """Get entity by ID."""
        ...

    @abstractmethod
    async def create(self, **kwargs: Any) -> T:
        """Create new entity."""
        ...

    @abstractmethod
    async def update(self, id: ID, **kwargs: Any) -> T | None:
        """Update existing entity."""
        ...

    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        ...


class AsyncCRUDRepository(AsyncRepository[T, ID]):
    """Generic async CRUD repository implementation.
    
    Provides complete CRUD operations for SQLAlchemy models with
    support for filtering and pagination from shared.dbs patterns.
    
    Example:
        >>> class UserRepository(AsyncCRUDRepository[User, int]):
        ...     @property
        ...     def model_class(self) -> type[User]:
        ...         return User
        ...
        >>> async with db.get_session() as session:
        ...     repo = UserRepository(session)
        ...     user = await repo.create(name="John", email="john@example.com")
        ...
        ...     # Using filters
        ...     filters = [Filter(field="name", operator=FilterOperator.CONTAINS, value="Jo")]
        ...     users = await repo.find_with_filters(filters)
        ...
        ...     # Using pagination
        ...     page = await repo.paginate(PageRequest(page=1, size=10))
    """

    def _apply_filter(self, stmt: Select, filter: Filter) -> Select:
        """Apply a single filter to a query statement.
        
        Args:
            stmt: SQLAlchemy select statement.
            filter: Filter to apply.
            
        Returns:
            Modified statement with filter applied.
        """
        column = getattr(self.model_class, filter.field, None)
        if column is None:
            return stmt
        
        match filter.operator:
            case FilterOperator.EQ:
                stmt = stmt.where(column == filter.value)
            case FilterOperator.NE:
                stmt = stmt.where(column != filter.value)
            case FilterOperator.GT:
                stmt = stmt.where(column > filter.value)
            case FilterOperator.GE | FilterOperator.GTE:
                stmt = stmt.where(column >= filter.value)
            case FilterOperator.LT:
                stmt = stmt.where(column < filter.value)
            case FilterOperator.LE | FilterOperator.LTE:
                stmt = stmt.where(column <= filter.value)
            case FilterOperator.LIKE:
                stmt = stmt.where(column.like(str(filter.value)))
            case FilterOperator.CONTAINS:
                stmt = stmt.where(column.contains(str(filter.value)))
            case FilterOperator.STARTS_WITH:
                stmt = stmt.where(column.startswith(str(filter.value)))
            case FilterOperator.ENDS_WITH:
                stmt = stmt.where(column.endswith(str(filter.value)))
            case FilterOperator.IN:
                if isinstance(filter.value, (list, tuple, set)):
                    stmt = stmt.where(column.in_(filter.value))
            case FilterOperator.NOT_IN:
                if isinstance(filter.value, (list, tuple, set)):
                    stmt = stmt.where(column.not_in(filter.value))
            case FilterOperator.IS_NULL:
                stmt = stmt.where(column.is_(None))
            case FilterOperator.IS_NOT_NULL:
                stmt = stmt.where(column.is_not(None))
        
        return stmt

    def _apply_filters(
        self, stmt: Select, filters: list[Filter] | None
    ) -> Select:
        """Apply multiple filters to a query statement.
        
        Args:
            stmt: SQLAlchemy select statement.
            filters: List of filters to apply.
            
        Returns:
            Modified statement with all filters applied.
        """
        if not filters:
            return stmt
        
        for filter in filters:
            stmt = self._apply_filter(stmt, filter)
        
        return stmt

    def _apply_ordering(
        self, stmt: Select, order_by: list[OrderBy] | None
    ) -> Select:
        """Apply ordering to a query statement.
        
        Args:
            stmt: SQLAlchemy select statement.
            order_by: List of ordering specifications.
            
        Returns:
            Modified statement with ordering applied.
        """
        if not order_by:
            return stmt
        
        for order in order_by:
            column = getattr(self.model_class, order.field, None)
            if column is not None:
                if order.direction == OrderDirection.DESC:
                    stmt = stmt.order_by(desc(column))
                else:
                    stmt = stmt.order_by(asc(column))
        
        return stmt

    async def get_by_id(self, id: ID) -> T | None:
        """Get entity by primary key.
        
        Args:
            id: Primary key value.
            
        Returns:
            Entity if found, None otherwise.
        """
        return await self._session.get(self.model_class, id)

    async def get_all(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Get all entities with optional pagination.
        
        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of entities.
        """
        stmt = select(self.model_class)
        
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        """Create new entity.
        
        Args:
            **kwargs: Entity attributes.
            
        Returns:
            Created entity with generated ID.
        """
        entity = self.model_class(**kwargs)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, id: ID, **kwargs: Any) -> T | None:
        """Update existing entity.
        
        Args:
            id: Primary key of entity to update.
            **kwargs: Attributes to update.
            
        Returns:
            Updated entity if found, None otherwise.
        """
        entity = await self.get_by_id(id)
        if entity is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: ID) -> bool:
        """Delete entity by ID.
        
        Args:
            id: Primary key of entity to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        entity = await self.get_by_id(id)
        if entity is None:
            return False
        
        await self._session.delete(entity)
        await self._session.flush()
        return True

    async def exists(self, id: ID) -> bool:
        """Check if entity exists.
        
        Args:
            id: Primary key to check.
            
        Returns:
            True if entity exists.
        """
        entity = await self.get_by_id(id)
        return entity is not None

    async def count(self, filters: list[Filter] | None = None) -> int:
        """Count entities, optionally with filters.
        
        Args:
            filters: Optional filters to apply.
            
        Returns:
            Number of matching entities.
        """
        stmt = select(func.count()).select_from(self.model_class)
        stmt = self._apply_filters(stmt, filters)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def find_with_filters(
        self,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Find entities with filters and ordering.
        
        Args:
            filters: List of filters to apply.
            order_by: List of ordering specifications.
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of matching entities.
        """
        stmt = select(self.model_class)
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_ordering(stmt, order_by)
        
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def paginate(
        self,
        page_request: PageRequest,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
    ) -> PageResponse[T]:
        """Get paginated results.
        
        Args:
            page_request: Pagination parameters.
            filters: Optional filters to apply.
            order_by: Optional ordering specifications.
            
        Returns:
            Paginated response with items and metadata.
            
        Example:
            >>> page = await repo.paginate(
            ...     PageRequest(page=1, size=10),
            ...     filters=[Filter(field="status", value="active")],
            ...     order_by=[OrderBy(field="created_at", direction=OrderDirection.DESC)]
            ... )
            >>> print(f"Page {page.page} of {page.total_pages}")
        """
        # Get total count
        total = await self.count(filters)
        
        # Calculate offset
        offset = (page_request.page - 1) * page_request.size
        
        # Get items
        items = await self.find_with_filters(
            filters=filters,
            order_by=order_by,
            limit=page_request.size,
            offset=offset,
        )
        
        return PageResponse(
            items=items,
            total=total,
            page=page_request.page,
            size=page_request.size,
        )

    async def find_by(self, **kwargs: Any) -> list[T]:
        """Find entities by attribute values.
        
        Args:
            **kwargs: Attribute name-value pairs to filter by.
            
        Returns:
            List of matching entities.
        """
        stmt = select(self.model_class)
        
        for key, value in kwargs.items():
            column = getattr(self.model_class, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_one_by(self, **kwargs: Any) -> T | None:
        """Find single entity by attribute values.
        
        Args:
            **kwargs: Attribute name-value pairs to filter by.
            
        Returns:
            First matching entity or None.
        """
        results = await self.find_by(**kwargs)
        return results[0] if results else None
