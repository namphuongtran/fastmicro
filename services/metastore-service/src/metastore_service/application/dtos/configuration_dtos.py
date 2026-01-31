"""DTOs for Configuration operations.

Data Transfer Objects for API request/response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from metastore_service.domain.value_objects import Environment


class SecretReferenceDTO(BaseModel):
    """DTO for secret reference."""

    key: str = Field(..., description="Configuration key that holds the secret")
    vault_path: str = Field(..., description="Path to the secret in the vault")
    vault_key: str = Field(..., description="Key within the vault secret")


class CreateConfigurationDTO(BaseModel):
    """DTO for creating a new configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_id": "order-service",
                "name": "database",
                "environment": "production",
                "values": {
                    "host": "db.example.com",
                    "port": 5432,
                    "pool_size": 10,
                    "timeout": 30,
                },
                "description": "Database configuration for order service",
                "secret_refs": [
                    {
                        "key": "password",
                        "vault_path": "secret/data/order-service",
                        "vault_key": "db_password",
                    }
                ],
            }
        }
    )

    service_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Service identifier",
        examples=["order-service", "user-service"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Configuration name",
        examples=["database", "cache", "api"],
    )
    environment: Environment = Field(
        ...,
        description="Deployment environment",
    )
    values: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration key-value pairs",
    )
    schema_id: UUID | None = Field(
        default=None,
        description="Optional schema ID for validation",
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
    effective_from: datetime | None = Field(
        default=None,
        description="When this configuration becomes effective",
    )
    secret_refs: list[SecretReferenceDTO] = Field(
        default_factory=list,
        description="References to secrets in external vault",
    )

    @field_validator("service_id", "name")
    @classmethod
    def validate_identifiers(cls, v: str) -> str:
        """Validate identifier format."""
        import re

        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(
                "Must be lowercase letters, numbers, and hyphens, starting with a letter"
            )
        return v


class UpdateConfigurationDTO(BaseModel):
    """DTO for updating an existing configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "values": {"pool_size": 20, "timeout": 60},
                "merge": True,
                "change_reason": "Increased pool size for higher load",
            }
        }
    )

    values: dict[str, Any] | None = Field(
        default=None,
        description="New configuration values",
    )
    merge: bool = Field(
        default=True,
        description="If True, merge with existing values; if False, replace",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    effective_from: datetime | None = Field(default=None)
    effective_until: datetime | None = Field(default=None)
    change_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason for the change (for audit)",
    )


class ConfigurationVersionDTO(BaseModel):
    """DTO for configuration version information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    values: dict[str, Any]
    created_at: datetime
    created_by: str | None = None
    change_reason: str | None = None


class ConfigurationDTO(BaseModel):
    """DTO for configuration response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: str
    name: str
    environment: Environment
    values: dict[str, Any]
    secret_keys: list[str]
    tenant_id: str | None = None
    description: str | None = None
    is_active: bool
    is_effective: bool
    effective_from: datetime | None
    effective_until: datetime | None
    current_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def from_entity(cls, entity, include_secrets: bool = False) -> ConfigurationDTO:
        """Convert domain entity to DTO."""
        return cls(
            id=entity.id,
            service_id=entity.service_id,
            name=entity.name,
            environment=entity.environment,
            values=entity.to_dict(include_secrets=include_secrets),
            secret_keys=entity.get_secret_keys(),
            tenant_id=entity.tenant_id.value if entity.tenant_id else None,
            description=entity.description,
            is_active=entity.is_active,
            is_effective=entity.is_effective,
            effective_from=entity.effective_from,
            effective_until=entity.effective_until,
            current_version=entity.current_version_number,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )


class ConfigurationListDTO(BaseModel):
    """DTO for paginated configuration list response."""

    items: list[ConfigurationDTO]
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
        include_secrets: bool = False,
    ) -> ConfigurationListDTO:
        """Convert list of entities to paginated DTO."""
        return cls(
            items=[ConfigurationDTO.from_entity(e, include_secrets) for e in entities],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(entities) < total,
        )


class CreateConfigurationSchemaDTO(BaseModel):
    """DTO for creating a configuration schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "database-config",
                "version": "1.0.0",
                "json_schema": {
                    "type": "object",
                    "required": ["host", "port"],
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "pool_size": {"type": "integer", "minimum": 1, "default": 10},
                    },
                },
                "description": "Schema for database configuration",
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Schema name",
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version (semver)",
    )
    json_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema definition",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )


class ConfigurationSchemaDTO(BaseModel):
    """DTO for configuration schema response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    json_schema: dict[str, Any]
    description: str | None = None

    @classmethod
    def from_entity(cls, entity) -> ConfigurationSchemaDTO:
        """Convert domain entity to DTO."""
        return cls(
            id=entity.id,
            name=entity.name,
            version=entity.version,
            json_schema=entity.json_schema,
            description=entity.description,
        )
