"""Core audit trail types and in-memory implementation.

This module defines the immutable :class:`AuditEvent` record, a set of
standard :class:`AuditAction` verbs, and the :class:`AuditLogger`
protocol that backends must satisfy.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4


class AuditAction(str, enum.Enum):
    """Standard audit action verbs.

    Extend with domain-specific values in service code as needed.
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    GRANT = "grant"
    REVOKE = "revoke"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit log entry.

    Attributes:
        event_id: Unique identifier for this audit record.
        action: The action that was performed.
        actor_id: Identity of the user or service that performed the action.
        actor_type: Category of actor (``user``, ``service``, ``system``).
        resource_type: Type of the affected resource (e.g. ``Order``, ``User``).
        resource_id: Identifier of the affected resource.
        description: Free-text description of the event.
        old_value: Snapshot of the resource *before* the change (optional).
        new_value: Snapshot of the resource *after* the change (optional).
        ip_address: Originating IP address.
        user_agent: Originating user-agent string.
        correlation_id: Distributed trace correlation ID.
        metadata: Arbitrary additional context.
        occurred_at: UTC timestamp when the event happened.
        service_name: Name of the service that emitted the event.
    """

    action: AuditAction | str
    actor_id: str
    resource_type: str
    resource_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    actor_type: str = "user"
    description: str = ""
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    service_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary (for JSON logging or persistence)."""
        action_value = (
            self.action.value if isinstance(self.action, AuditAction) else str(self.action)
        )
        return {
            "event_id": self.event_id,
            "action": action_value,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "occurred_at": self.occurred_at.isoformat(),
            "service_name": self.service_name,
        }


@dataclass
class AuditQuery:
    """Query parameters for searching audit records.

    All fields are optional; combine to narrow results.
    """

    actor_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: AuditAction | str | None = None
    service_name: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    limit: int = 50
    offset: int = 0


@runtime_checkable
class AuditLogger(Protocol):
    """Protocol that all audit backends must satisfy.

    Implementations may write to a database, message queue,
    external service, or structured log sink.
    """

    async def log(self, event: AuditEvent) -> None:
        """Persist a single audit event."""
        ...

    async def log_many(self, events: list[AuditEvent]) -> None:
        """Persist multiple audit events in a batch."""
        ...

    async def query(self, query: AuditQuery) -> list[AuditEvent]:
        """Retrieve audit events matching the given criteria."""
        ...


class InMemoryAuditLogger:
    """In-memory audit logger for tests and development.

    Stores events in a plain list.  **Not** intended for production use.

    Example:
        >>> logger = InMemoryAuditLogger()
        >>> await logger.log(AuditEvent(
        ...     action=AuditAction.CREATE,
        ...     actor_id="usr-1",
        ...     resource_type="User",
        ... ))
        >>> assert len(logger.events) == 1
    """

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def log(self, event: AuditEvent) -> None:
        """Append event to the in-memory list."""
        self.events.append(event)

    async def log_many(self, events: list[AuditEvent]) -> None:
        """Append multiple events."""
        self.events.extend(events)

    async def query(self, query: AuditQuery) -> list[AuditEvent]:
        """Filter in-memory events by query criteria."""
        results = list(self.events)

        if query.actor_id:
            results = [e for e in results if e.actor_id == query.actor_id]
        if query.resource_type:
            results = [e for e in results if e.resource_type == query.resource_type]
        if query.resource_id:
            results = [e for e in results if e.resource_id == query.resource_id]
        if query.action:
            action_str = str(query.action)
            results = [e for e in results if str(e.action) == action_str]
        if query.service_name:
            results = [e for e in results if e.service_name == query.service_name]
        if query.from_date:
            results = [e for e in results if e.occurred_at >= query.from_date]
        if query.to_date:
            results = [e for e in results if e.occurred_at <= query.to_date]

        return results[query.offset : query.offset + query.limit]

    def clear(self) -> None:
        """Remove all stored events."""
        self.events.clear()
