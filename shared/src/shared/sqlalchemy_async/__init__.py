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

# Re-export from shared.dbs for convenience
from shared.dbs.repository import (
    Filter,
    FilterOperator,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)
from shared.sqlalchemy_async.database import (
    AsyncDatabaseManager,
    DatabaseConfig,
    get_async_session,
)
from shared.sqlalchemy_async.models import (
    AuditMixin,
    FullAuditMixin,
    SoftDeleteMixin,
    TenantAuditMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from shared.sqlalchemy_async.repository import (
    AsyncCRUDRepository,
    AsyncRepository,
)
from shared.sqlalchemy_async.instrumentation import (
    SQLAlchemyInstrumentationConfig,
    configure_sqlalchemy_instrumentation,
    instrument_engine,
    reset_sqlalchemy_instrumentation,
    uninstrument_engine,
)
from shared.sqlalchemy_async.migrations import (
    AlembicMigrationConfig,
    create_alembic_config,
    generate_migration_scaffold,
    get_current_revision,
    run_downgrade,
    run_upgrade_to_head,
    stamp_head,
)
from shared.sqlalchemy_async.unit_of_work import SqlAlchemyUnitOfWork

__all__ = [
    # Database management
    "AsyncDatabaseManager",
    "DatabaseConfig",
    "get_async_session",
    # Repository pattern
    "AsyncRepository",
    "AsyncCRUDRepository",
    # Unit of Work
    "SqlAlchemyUnitOfWork",
    # Instrumentation
    "SQLAlchemyInstrumentationConfig",
    "configure_sqlalchemy_instrumentation",
    "instrument_engine",
    "uninstrument_engine",
    "reset_sqlalchemy_instrumentation",
    # Migrations
    "AlembicMigrationConfig",
    "create_alembic_config",
    "generate_migration_scaffold",
    "get_current_revision",
    "run_upgrade_to_head",
    "run_downgrade",
    "stamp_head",
    # Model mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "UUIDPrimaryKeyMixin",
    "AuditMixin",
    "TenantMixin",
    "VersionMixin",
    "FullAuditMixin",
    "TenantAuditMixin",
    # Query utilities (from shared.dbs)
    "Filter",
    "FilterOperator",
    "OrderBy",
    "OrderDirection",
    "PageRequest",
    "PageResponse",
]
