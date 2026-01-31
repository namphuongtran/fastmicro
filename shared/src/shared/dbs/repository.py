"""Generic Repository pattern implementation.

This module provides abstract and in-memory repository implementations
with filtering, ordering, and pagination support.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class FilterOperator(Enum):
    """Filter comparison operators."""
    
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    GTE = "gte"  # Alias for GE
    LT = "lt"
    LE = "le"
    LTE = "lte"  # Alias for LE
    LIKE = "like"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class OrderDirection(Enum):
    """Order direction."""
    
    ASC = "asc"
    DESC = "desc"


@dataclass
class Filter:
    """Filter specification for queries."""
    
    field: str
    value: Any
    operator: FilterOperator = FilterOperator.EQ


@dataclass
class OrderBy:
    """Order specification for queries."""
    
    field: str
    direction: OrderDirection = OrderDirection.ASC


@dataclass
class PageRequest:
    """Pagination request parameters."""
    
    page: int = 1
    size: int = 10

    @property
    def offset(self) -> int:
        """Calculate offset for database query.
        
        Returns:
            The offset value.
        """
        return (self.page - 1) * self.size


@dataclass
class PageResponse(Generic[T]):
    """Paginated response with metadata."""
    
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages.
        
        Returns:
            Total pages.
        """
        return math.ceil(self.total / self.size) if self.size > 0 else 0

    @property
    def has_next(self) -> bool:
        """Check if there is a next page.
        
        Returns:
            True if next page exists.
        """
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page.
        
        Returns:
            True if previous page exists.
        """
        return self.page > 1


class AbstractRepository(ABC, Generic[T]):
    """Abstract repository interface.
    
    Defines the standard CRUD operations and query methods
    that all repositories must implement.
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add a new entity.
        
        Args:
            entity: The entity to add.
            
        Returns:
            The added entity.
        """
        ...

    @abstractmethod
    async def get(self, id: str) -> T | None:
        """Get entity by ID.
        
        Args:
            id: The entity ID.
            
        Returns:
            The entity or None if not found.
        """
        ...

    @abstractmethod
    async def get_all(self) -> list[T]:
        """Get all entities.
        
        Returns:
            List of all entities.
        """
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity.
        
        Args:
            entity: The entity to update.
            
        Returns:
            The updated entity.
        """
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID.
        
        Args:
            id: The entity ID.
            
        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if entity exists.
        
        Args:
            id: The entity ID.
            
        Returns:
            True if exists.
        """
        ...

    @abstractmethod
    async def count(self, filters: list[Filter] | None = None) -> int:
        """Count entities.
        
        Args:
            filters: Optional filters to apply.
            
        Returns:
            Number of entities.
        """
        ...


class InMemoryRepository(AbstractRepository[T]):
    """In-memory repository implementation.
    
    Useful for testing and prototyping. Stores entities in a dict.
    """

    def __init__(self, id_field: str = "id") -> None:
        """Initialize the repository.
        
        Args:
            id_field: Name of the ID field on entities.
        """
        self._storage: dict[str, T] = {}
        self._id_field = id_field

    def _get_id(self, entity: T) -> str:
        """Get ID from entity.
        
        Args:
            entity: The entity.
            
        Returns:
            The entity ID.
        """
        return str(getattr(entity, self._id_field))

    def _matches_filter(self, entity: T, filter: Filter) -> bool:
        """Check if entity matches a filter.
        
        Args:
            entity: The entity to check.
            filter: The filter to apply.
            
        Returns:
            True if entity matches.
        """
        value = getattr(entity, filter.field, None)
        
        match filter.operator:
            case FilterOperator.EQ:
                return value == filter.value
            case FilterOperator.NE:
                return value != filter.value
            case FilterOperator.GT:
                return value > filter.value
            case FilterOperator.GTE:
                return value >= filter.value
            case FilterOperator.LT:
                return value < filter.value
            case FilterOperator.LTE:
                return value <= filter.value
            case FilterOperator.LIKE:
                return filter.value.lower() in str(value).lower()
            case FilterOperator.IN:
                return value in filter.value
            case _:
                return False

    def _apply_filters(self, entities: list[T], filters: list[Filter]) -> list[T]:
        """Apply filters to entity list.
        
        Args:
            entities: List of entities.
            filters: Filters to apply.
            
        Returns:
            Filtered list.
        """
        result = entities
        for f in filters:
            result = [e for e in result if self._matches_filter(e, f)]
        return result

    def _apply_ordering(self, entities: list[T], order_by: list[OrderBy]) -> list[T]:
        """Apply ordering to entity list.
        
        Args:
            entities: List of entities.
            order_by: Ordering specifications.
            
        Returns:
            Ordered list.
        """
        result = entities
        for order in reversed(order_by):
            reverse = order.direction == OrderDirection.DESC
            result = sorted(
                result,
                key=lambda e: getattr(e, order.field, ""),
                reverse=reverse,
            )
        return result

    async def add(self, entity: T) -> T:
        """Add a new entity."""
        entity_id = self._get_id(entity)
        self._storage[entity_id] = entity
        return entity

    async def get(self, id: str) -> T | None:
        """Get entity by ID."""
        return self._storage.get(id)

    async def get_all(self) -> list[T]:
        """Get all entities."""
        return list(self._storage.values())

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        entity_id = self._get_id(entity)
        self._storage[entity_id] = entity
        return entity

    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        return id in self._storage

    async def count(self, filters: list[Filter] | None = None) -> int:
        """Count entities."""
        if filters:
            entities = await self.find(filters=filters)
            return len(entities)
        return len(self._storage)

    async def find(
        self,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
    ) -> list[T]:
        """Find entities with filters and ordering.
        
        Args:
            filters: Optional filters.
            order_by: Optional ordering.
            
        Returns:
            List of matching entities.
        """
        result = list(self._storage.values())
        
        if filters:
            result = self._apply_filters(result, filters)
        
        if order_by:
            result = self._apply_ordering(result, order_by)
        
        return result

    async def find_one(
        self,
        filters: list[Filter] | None = None,
    ) -> T | None:
        """Find first matching entity.
        
        Args:
            filters: Optional filters.
            
        Returns:
            First matching entity or None.
        """
        result = await self.find(filters=filters)
        return result[0] if result else None

    async def find_paginated(
        self,
        page_request: PageRequest,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
    ) -> PageResponse[T]:
        """Find entities with pagination.
        
        Args:
            page_request: Pagination parameters.
            filters: Optional filters.
            order_by: Optional ordering.
            
        Returns:
            Paginated response.
        """
        all_items = await self.find(filters=filters, order_by=order_by)
        total = len(all_items)
        
        start = page_request.offset
        end = start + page_request.size
        items = all_items[start:end]
        
        return PageResponse(
            items=items,
            total=total,
            page=page_request.page,
            size=page_request.size,
        )

    async def clear(self) -> None:
        """Remove all entities."""
        self._storage.clear()


__all__ = [
    "FilterOperator",
    "OrderDirection",
    "Filter",
    "OrderBy",
    "PageRequest",
    "PageResponse",
    "AbstractRepository",
    "InMemoryRepository",
]
