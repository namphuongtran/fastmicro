"""SQLAlchemy model mixins and utilities.

This module provides reusable mixins for SQLAlchemy models:
- TimestampMixin: Automatic created_at/updated_at timestamps
- SoftDeleteMixin: Soft delete functionality
- UUIDPrimaryKeyMixin: UUID primary key generation
- AuditMixin: User audit fields (created_by, updated_by)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, event
from sqlalchemy.orm import Mapped, mapped_column, declared_attr


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
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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
        self.deleted_at = datetime.now(timezone.utc)

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
