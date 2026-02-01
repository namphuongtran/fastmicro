"""SQLAlchemy model mixins and utilities.

This module provides reusable mixins for SQLAlchemy models:
- TimestampMixin: Automatic created_at/updated_at timestamps
- SoftDeleteMixin: Soft delete functionality
- UUIDPrimaryKeyMixin: UUID primary key generation
- AuditMixin: User audit fields (created_by, updated_by)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mixin that adds automatic timestamp columns.
    
    Adds created_at and updated_at columns that are automatically
    managed on insert and update operations.
    
    Example:
        >>> class User(TimestampMixin, Base):
        ...     __tablename__ = "users"
        ...     id = Column(Integer, primary_key=True)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality.
    
    Instead of actually deleting records, marks them as deleted
    with is_deleted flag and deleted_at timestamp.
    
    Example:
        >>> class Document(SoftDeleteMixin, Base):
        ...     __tablename__ = "documents"
        ...     id = Column(Integer, primary_key=True)
        ...
        >>> doc.soft_delete()  # Mark as deleted
        >>> doc.restore()  # Restore
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def soft_delete(self) -> None:
        """Mark entity as soft deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore soft deleted entity."""
        self.is_deleted = False
        self.deleted_at = None


class UUIDPrimaryKeyMixin:
    """Mixin that provides UUID primary key.
    
    Generates UUID4 as the primary key for the model.
    
    Example:
        >>> class Event(UUIDPrimaryKeyMixin, Base):
        ...     __tablename__ = "events"
        ...     name = Column(String(100))
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class AuditMixin:
    """Mixin that adds user audit fields.
    
    Tracks which user created and last updated the entity.
    
    Example:
        >>> class Order(AuditMixin, Base):
        ...     __tablename__ = "orders"
        ...     id = Column(Integer, primary_key=True)
        ...
        >>> order = Order(created_by="user123")
    """

    created_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


class TenantMixin:
    """Mixin that adds multi-tenant support.
    
    Adds a tenant_id column for multi-tenant data isolation.
    
    Example:
        >>> class Document(TenantMixin, Base):
        ...     __tablename__ = "documents"
        ...     id = Column(Integer, primary_key=True)
        ...
        >>> doc = Document(tenant_id="tenant-123")
    """

    tenant_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )


class VersionMixin:
    """Mixin for optimistic concurrency control.
    
    Adds a version column that auto-increments on updates.
    Use with SQLAlchemy's version_id_col for optimistic locking.
    
    Example:
        >>> class Order(VersionMixin, Base):
        ...     __tablename__ = "orders"
        ...     __mapper_args__ = {"version_id_col": "version"}
        ...     id = Column(Integer, primary_key=True)
    """

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    def increment_version(self) -> None:
        """Manually increment version."""
        self.version += 1


class FullAuditMixin(TimestampMixin, AuditMixin, VersionMixin):
    """Combined mixin with timestamps, user audit, and versioning.
    
    Provides complete audit trail for entities.
    
    Example:
        >>> class Invoice(FullAuditMixin, Base):
        ...     __tablename__ = "invoices"
        ...     id = Column(Integer, primary_key=True)
    """
    pass


class TenantAuditMixin(TimestampMixin, AuditMixin, TenantMixin):
    """Combined mixin with timestamps, user audit, and multi-tenancy.
    
    Ideal for multi-tenant applications requiring audit trails.
    
    Example:
        >>> class Contract(TenantAuditMixin, Base):
        ...     __tablename__ = "contracts"
        ...     id = Column(Integer, primary_key=True)
    """
    pass
