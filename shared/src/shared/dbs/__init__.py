"""Database patterns and utilities for microservices.

This module provides enterprise patterns for database operations:
- Repository pattern for data access abstraction
- Unit of Work pattern for transaction management
- Query building utilities
"""

from __future__ import annotations

from shared.dbs.repository import (
    AbstractRepository,
    Filter,
    FilterOperator,
    InMemoryRepository,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)
from shared.dbs.unit_of_work import (
    AbstractUnitOfWork,
    InMemoryUnitOfWork,
)

__all__ = [
    # Repository
    "FilterOperator",
    "OrderDirection",
    "Filter",
    "OrderBy",
    "PageRequest",
    "PageResponse",
    "AbstractRepository",
    "InMemoryRepository",
    # Unit of Work
    "AbstractUnitOfWork",
    "InMemoryUnitOfWork",
]
