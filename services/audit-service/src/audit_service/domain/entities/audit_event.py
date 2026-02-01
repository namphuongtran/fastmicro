"""
Audit Event domain entity.

Defines the core domain model for audit events including actions, severity levels,
and the main AuditEvent entity.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SUBMIT = "SUBMIT"
    CANCEL = "CANCEL"
    EXECUTE = "EXECUTE"
    CONFIGURE = "CONFIGURE"
    GRANT = "GRANT"
    REVOKE = "REVOKE"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEvent(BaseModel):
    """
    Core domain entity for audit events.

    Represents a single audit log entry capturing an action performed
    by an actor on a resource.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")

    # Event metadata
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp in UTC",
    )
    service_name: str = Field(description="Source service name")
    correlation_id: str | None = Field(default=None, description="Request correlation ID")

    # Actor information
    actor_id: str = Field(description="ID of the actor performing the action")
    actor_type: str = Field(default="user", description="Type of actor (user, service, system)")
    actor_name: str | None = Field(default=None, description="Human-readable actor name")
    actor_email: str | None = Field(default=None, description="Actor email address")
    actor_ip: str | None = Field(default=None, description="Actor IP address")
    actor_user_agent: str | None = Field(default=None, description="Actor user agent")

    # Action details
    action: AuditAction = Field(description="Action performed")
    severity: AuditSeverity = Field(default=AuditSeverity.INFO, description="Event severity")

    # Resource information
    resource_type: str = Field(description="Type of resource affected")
    resource_id: str = Field(description="ID of the affected resource")
    resource_name: str | None = Field(default=None, description="Human-readable resource name")

    # Additional context
    description: str | None = Field(default=None, description="Human-readable event description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    old_value: dict[str, Any] | None = Field(
        default=None, description="Previous state (for updates)"
    )
    new_value: dict[str, Any] | None = Field(default=None, description="New state (for updates)")

    # Compliance
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance tags (GDPR, SOC2, HIPAA, etc.)",
    )

    model_config = ConfigDict(from_attributes=True)


class CreateAuditEventRequest(BaseModel):
    """Request model for creating audit events."""

    service_name: str = Field(description="Source service name")
    correlation_id: str | None = Field(default=None, description="Request correlation ID")

    # Actor information
    actor_id: str = Field(description="ID of the actor performing the action")
    actor_type: str = Field(default="user", description="Type of actor")
    actor_name: str | None = Field(default=None, description="Human-readable actor name")
    actor_email: str | None = Field(default=None, description="Actor email address")
    actor_ip: str | None = Field(default=None, description="Actor IP address")
    actor_user_agent: str | None = Field(default=None, description="Actor user agent")

    # Action details
    action: AuditAction = Field(description="Action performed")
    severity: AuditSeverity = Field(default=AuditSeverity.INFO, description="Event severity")

    # Resource information
    resource_type: str = Field(description="Type of resource affected")
    resource_id: str = Field(description="ID of the affected resource")
    resource_name: str | None = Field(default=None, description="Human-readable resource name")

    # Additional context
    description: str | None = Field(default=None, description="Human-readable event description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    old_value: dict[str, Any] | None = Field(default=None, description="Previous state")
    new_value: dict[str, Any] | None = Field(default=None, description="New state")

    # Compliance
    compliance_tags: list[str] = Field(default_factory=list, description="Compliance tags")


class AuditEventResponse(BaseModel):
    """Response model for audit events."""

    id: UUID = Field(description="Unique event identifier")
    timestamp: datetime = Field(description="Event timestamp")
    service_name: str = Field(description="Source service name")
    correlation_id: str | None = Field(description="Request correlation ID")

    actor_id: str = Field(description="Actor ID")
    actor_type: str = Field(description="Actor type")
    actor_name: str | None = Field(description="Actor name")

    action: AuditAction = Field(description="Action performed")
    severity: AuditSeverity = Field(description="Event severity")

    resource_type: str = Field(description="Resource type")
    resource_id: str = Field(description="Resource ID")
    resource_name: str | None = Field(description="Resource name")

    description: str | None = Field(description="Event description")
    compliance_tags: list[str] = Field(description="Compliance tags")

    model_config = ConfigDict(from_attributes=True)
