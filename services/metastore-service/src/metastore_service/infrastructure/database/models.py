"""SQLAlchemy database models for the Metastore Service.

These models map domain entities to the PostgreSQL database schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from metastore_service.domain.value_objects import ContentType, Environment, Operator


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class MetadataEntryModel(Base):
    """SQLAlchemy model for metadata entries."""

    __tablename__ = "metadata_entries"
    __table_args__ = (
        UniqueConstraint("key", "namespace", "tenant_id", name="uq_metadata_key_namespace_tenant"),
        Index("ix_metadata_namespace", "namespace"),
        Index("ix_metadata_tenant", "tenant_id"),
        Index("ix_metadata_tags", "tags", postgresql_using="gin"),
        Index("ix_metadata_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    namespace: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    current_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type_enum"),
        nullable=False,
        default=ContentType.JSON,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    versions: Mapped[list[MetadataVersionModel]] = relationship(
        "MetadataVersionModel",
        back_populates="metadata_entry",
        cascade="all, delete-orphan",
        order_by="desc(MetadataVersionModel.version_number)",
    )


class MetadataVersionModel(Base):
    """SQLAlchemy model for metadata version history."""

    __tablename__ = "metadata_versions"
    __table_args__ = (
        Index("ix_metadata_version_metadata_id", "metadata_id"),
        Index("ix_metadata_version_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    metadata_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("metadata_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    metadata_entry: Mapped[MetadataEntryModel] = relationship(
        "MetadataEntryModel",
        back_populates="versions",
    )


class FeatureFlagModel(Base):
    """SQLAlchemy model for feature flags."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("name", name="uq_feature_flag_name"),
        Index("ix_feature_flag_enabled", "enabled"),
        Index("ix_feature_flag_tags", "tags", postgresql_using="gin"),
        Index("ix_feature_flag_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_value: Mapped[Any] = mapped_column(JSONB, nullable=False, default=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    tenant_overrides: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    environment_overrides: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    targeting_rules: Mapped[list[TargetingRuleModel]] = relationship(
        "TargetingRuleModel",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
        order_by="TargetingRuleModel.priority",
    )


class TargetingRuleModel(Base):
    """SQLAlchemy model for feature flag targeting rules."""

    __tablename__ = "targeting_rules"
    __table_args__ = (
        Index("ix_targeting_rule_flag_id", "feature_flag_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    feature_flag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("feature_flags.id", ondelete="CASCADE"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    operator: Mapped[Operator] = mapped_column(
        Enum(Operator, name="operator_enum"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    feature_flag: Mapped[FeatureFlagModel] = relationship(
        "FeatureFlagModel",
        back_populates="targeting_rules",
    )


class ConfigurationModel(Base):
    """SQLAlchemy model for service configurations."""

    __tablename__ = "configurations"
    __table_args__ = (
        UniqueConstraint(
            "service_id", "name", "environment", "tenant_id",
            name="uq_config_service_name_env_tenant",
        ),
        Index("ix_config_service_id", "service_id"),
        Index("ix_config_environment", "environment"),
        Index("ix_config_tenant", "tenant_id"),
        Index("ix_config_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[Environment] = mapped_column(
        Enum(Environment, name="environment_enum"),
        nullable=False,
    )
    values: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    schema_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("configuration_schemas.id", ondelete="SET NULL"),
        nullable=True,
    )
    secret_refs: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=[])
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    versions: Mapped[list[ConfigurationVersionModel]] = relationship(
        "ConfigurationVersionModel",
        back_populates="configuration",
        cascade="all, delete-orphan",
        order_by="desc(ConfigurationVersionModel.version_number)",
    )
    schema: Mapped[ConfigurationSchemaModel | None] = relationship(
        "ConfigurationSchemaModel",
        back_populates="configurations",
    )


class ConfigurationVersionModel(Base):
    """SQLAlchemy model for configuration version history."""

    __tablename__ = "configuration_versions"
    __table_args__ = (
        Index("ix_config_version_config_id", "configuration_id"),
        Index("ix_config_version_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    configuration_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("configurations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    configuration: Mapped[ConfigurationModel] = relationship(
        "ConfigurationModel",
        back_populates="versions",
    )


class ConfigurationSchemaModel(Base):
    """SQLAlchemy model for configuration schemas."""

    __tablename__ = "configuration_schemas"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_schema_name_version"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    json_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    configurations: Mapped[list[ConfigurationModel]] = relationship(
        "ConfigurationModel",
        back_populates="schema",
    )
