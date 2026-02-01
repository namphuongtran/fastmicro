"""DTOs for Feature Flag operations.

Data Transfer Objects for API request/response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from metastore_service.domain.value_objects import Environment, Operator


class TargetingRuleDTO(BaseModel):
    """DTO for targeting rule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    priority: int = Field(
        default=0,
        ge=0,
        description="Rule priority (lower = higher priority)",
    )
    attribute: str = Field(
        ...,
        description="Context attribute to match (e.g., 'user.email')",
        examples=["user.email", "user.country", "device.type"],
    )
    operator: Operator = Field(
        ...,
        description="Comparison operator",
    )
    value: str = Field(
        ...,
        description="Value to compare against",
        examples=["@company.com", "US,CA,UK"],
    )
    result: Any = Field(
        ...,
        description="Value to return if rule matches",
        examples=[True, "variant-a", {"theme": "dark"}],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Rule description",
    )


class CreateFeatureFlagDTO(BaseModel):
    """DTO for creating a new feature flag."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "new-checkout-flow",
                "description": "Enable new checkout experience",
                "enabled": True,
                "default_value": False,
                "rollout_percentage": 25,
                "tags": ["checkout", "experiment"],
                "targeting_rules": [
                    {
                        "attribute": "user.email",
                        "operator": "ends_with",
                        "value": "@company.com",
                        "result": True,
                        "description": "Enable for all internal users",
                    }
                ],
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique feature flag name (kebab-case)",
        examples=["new-checkout-flow", "dark-mode-beta"],
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Human-readable description",
    )
    enabled: bool = Field(
        default=False,
        description="Whether the flag is globally enabled",
    )
    default_value: Any = Field(
        default=False,
        description="Default value when no rules match",
    )
    rollout_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage of users to enable for (0-100)",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration datetime",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    targeting_rules: list[TargetingRuleDTO] = Field(
        default_factory=list,
        description="Targeting rules for conditional evaluation",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is kebab-case."""
        import re

        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError("Name must be kebab-case: lowercase letters, numbers, and hyphens")
        return v


class UpdateFeatureFlagDTO(BaseModel):
    """DTO for updating an existing feature flag."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated description",
                "rollout_percentage": 50,
                "enabled": True,
            }
        }
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    enabled: bool | None = Field(default=None)
    default_value: Any | None = Field(default=None)
    rollout_percentage: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    expires_at: datetime | None = Field(default=None)
    tags: list[str] | None = Field(default=None)


class EvaluateFeatureFlagDTO(BaseModel):
    """DTO for feature flag evaluation request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context": {
                    "user": {
                        "id": "user-123",
                        "email": "test@company.com",
                        "country": "US",
                    },
                    "device": {"type": "mobile", "os": "ios"},
                },
                "tenant_id": "tenant-abc",
                "environment": "production",
            }
        }
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context for targeting evaluation",
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant identifier",
    )
    environment: Environment | None = Field(
        default=None,
        description="Environment for override lookup",
    )


class FeatureFlagDTO(BaseModel):
    """DTO for feature flag response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    enabled: bool
    default_value: Any
    rollout_percentage: int
    targeting_rules: list[TargetingRuleDTO]
    tenant_overrides: dict[str, Any]
    environment_overrides: dict[str, Any]
    expires_at: datetime | None = None
    is_expired: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def from_entity(cls, entity) -> FeatureFlagDTO:
        """Convert domain entity to DTO."""
        return cls(
            id=entity.id,
            name=entity.name.value,
            description=entity.description,
            enabled=entity.enabled,
            default_value=entity.default_value,
            rollout_percentage=entity.rollout_percentage.value,
            targeting_rules=[
                TargetingRuleDTO(
                    id=r.id,
                    priority=r.priority,
                    attribute=r.attribute,
                    operator=r.operator,
                    value=r.value,
                    result=r.result,
                    description=r.description,
                )
                for r in entity.targeting_rules
            ],
            tenant_overrides=entity.tenant_overrides,
            environment_overrides={
                env.value: val for env, val in entity.environment_overrides.items()
            },
            expires_at=entity.expires_at,
            is_expired=entity.is_expired,
            tags=entity.tags,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )


class FeatureFlagListDTO(BaseModel):
    """DTO for paginated feature flag list response."""

    items: list[FeatureFlagDTO]
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
    ) -> FeatureFlagListDTO:
        """Convert list of entities to paginated DTO."""
        return cls(
            items=[FeatureFlagDTO.from_entity(e) for e in entities],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(entities) < total,
        )


class BulkEvaluateRequestDTO(BaseModel):
    """DTO for bulk feature flag evaluation request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flags": ["new-checkout-flow", "dark-mode-beta"],
                "context": {"user": {"id": "user-123"}},
            }
        }
    )

    flags: list[str] = Field(
        ...,
        min_length=1,
        description="List of feature flag names to evaluate",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context for targeting evaluation",
    )
    tenant_id: str | None = Field(default=None)
    environment: Environment | None = Field(default=None)


class BulkEvaluateResponseDTO(BaseModel):
    """DTO for bulk feature flag evaluation response."""

    values: dict[str, Any] = Field(
        ...,
        description="Map of flag name to evaluated value",
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Map of flag name to error message if evaluation failed",
    )
