"""Async SQLAlchemy utilities for FastAPI microservices.

This module provides enterprise-ready SQLAlchemy async utilities:
- AsyncDatabaseManager: Database connection management
- AsyncCRUDRepository: Generic repository pattern with filtering/pagination
- Model mixins for common patterns

Integrates with shared.dbs for abstract patterns (Filter, PageRequest, etc.)

Example:
    >>> from shared.sqlalchemy_async import (
    ...     AsyncDatabaseManager,
    ...     DatabaseConfig,
    ...     AsyncCRUDRepository,
    ...     TimestampMixin,
    ...     Filter,
    ...     FilterOperator,
    ...     PageRequest,
    ... )
    ...
    >>> config = DatabaseConfig(url="postgresql+asyncpg://localhost/mydb")
    >>> db = AsyncDatabaseManager(config)
    ...
    >>> async with db.get_session() as session:
    ...     repo = UserRepository(session)
    ...     # Use filtering
    ...     users = await repo.find_with_filters([
    ...         Filter(field="status", operator=FilterOperator.EQ, value="active")
    ...     ])
    ...     # Use pagination
    ...     page = await repo.paginate(PageRequest(page=1, size=10))
"""

from shared.sqlalchemy_async.database import (
    AsyncDatabaseManager,
    DatabaseConfig,
    get_async_session,
)
from shared.sqlalchemy_async.repository import (
    AsyncRepository,
    AsyncCRUDRepository,
)
from shared.sqlalchemy_async.models import (
    TimestampMixin,
    SoftDeleteMixin,
    UUIDPrimaryKeyMixin,
    AuditMixin,
)
# Re-export from shared.dbs for convenience
from shared.dbs.repository import (
    Filter,
    FilterOperator,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)

__all__ = [
    # Database management
    "AsyncDatabaseManager",
    "DatabaseConfig",
    "get_async_session",
    # Repository pattern
    "AsyncRepository",
    "AsyncCRUDRepository",
    # Model mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "UUIDPrimaryKeyMixin",
    "AuditMixin",
    # Query utilities (from shared.dbs)
    "Filter",
    "FilterOperator",
    "OrderBy",
    "OrderDirection",
    "PageRequest",
    "PageResponse",
]
