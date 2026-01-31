"""DTOs for Metadata operations.

Data Transfer Objects for API request/response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from metastore_service.domain.value_objects import ContentType


class CreateMetadataDTO(BaseModel):
    """DTO for creating a new metadata entry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "database.connection_string",
                "value": {"host": "localhost", "port": 5432},
                "namespace": "app.settings",
                "content_type": "json",
                "tags": ["database", "connection"],
                "description": "Database connection configuration",
                "is_encrypted": False,
                "is_secret": False,
            }
        }
    )

    key: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The metadata key",
        examples=["database.connection_string"],
    )
    value: Any = Field(
        ...,
        description="The metadata value (any JSON-serializable type)",
    )
    namespace: str = Field(
        default="default",
        max_length=255,
        description="Logical grouping namespace",
        examples=["app.settings", "feature.config"],
    )
    content_type: ContentType = Field(
        default=ContentType.JSON,
        description="Content type of the value",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
        examples=[["database", "connection"]],
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant identifier for multi-tenancy",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Human-readable description",
    )
    is_encrypted: bool = Field(
        default=False,
        description="Whether to encrypt the value at rest",
    )
    is_secret: bool = Field(
        default=False,
        description="Whether this is sensitive data",
    )

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate key format."""
        import re

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", v):
            raise ValueError(
                "Key must start with a letter and contain only "
                "alphanumeric characters, dots, underscores, and hyphens"
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and normalize tags."""
        return [tag.lower().strip() for tag in v if tag.strip()]


class UpdateMetadataDTO(BaseModel):
    """DTO for updating an existing metadata entry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": {"host": "production-db", "port": 5432},
                "tags": ["database", "production"],
                "change_reason": "Updated for production deployment",
            }
        }
    )

    value: Any | None = Field(
        default=None,
        description="New value (if updating)",
    )
    tags: list[str] | None = Field(
        default=None,
        description="New tags (replaces existing)",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Updated description",
    )
    is_encrypted: bool | None = Field(
        default=None,
        description="Whether to encrypt the value",
    )
    is_secret: bool | None = Field(
        default=None,
        description="Whether this is sensitive",
    )
    change_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason for the change (for audit)",
    )


class MetadataVersionDTO(BaseModel):
    """DTO for metadata version information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    value: Any
    created_at: datetime
    created_by: str | None = None
    change_reason: str | None = None


class MetadataDTO(BaseModel):
    """DTO for metadata entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    namespace: str
    value: Any
    content_type: ContentType
    tags: list[str]
    tenant_id: str | None = None
    description: str | None = None
    is_encrypted: bool = False
    is_secret: bool = False
    current_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def from_entity(cls, entity) -> MetadataDTO:
        """Convert domain entity to DTO."""
        return cls(
            id=entity.id,
            key=entity.key.value,
            namespace=entity.namespace.value,
            value=entity.current_value.raw_value if not entity.is_secret else "***REDACTED***",
            content_type=entity.content_type,
            tags=[t.value for t in entity.tags],
            tenant_id=entity.tenant_id.value if entity.tenant_id else None,
            description=entity.description,
            is_encrypted=entity.is_encrypted,
            is_secret=entity.is_secret,
            current_version=entity.current_version_number,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )


class MetadataListDTO(BaseModel):
    """DTO for paginated metadata list response."""

    items: list[MetadataDTO]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def from_entities(
        cls,
        entities: list,
        total: int,
        limit: int,
        offset: int,
    ) -> MetadataListDTO:
        """Convert list of entities to paginated DTO."""
        return cls(
            items=[MetadataDTO.from_entity(e) for e in entities],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(entities) < total,
        )
