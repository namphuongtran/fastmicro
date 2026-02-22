"""Enterprise audit trail module.

Provides structured audit logging for compliance requirements
(GDPR, SOC 2, HIPAA).  Captures *who* did *what*, *when*,
to *which entity*, from *where*.

Components:
- :class:`AuditEvent` — immutable audit record (dataclass)
- :class:`AuditAction` — standard action verbs
- :class:`AuditLogger` — protocol for writing audit events
- :class:`InMemoryAuditLogger` — test / development implementation
- :func:`audit_log` — decorator for automatic audit logging

Example:
    >>> from shared.audit import AuditEvent, AuditAction, InMemoryAuditLogger
    >>>
    >>> logger = InMemoryAuditLogger()
    >>> event = AuditEvent(
    ...     action=AuditAction.CREATE,
    ...     actor_id="user-123",
    ...     resource_type="Order",
    ...     resource_id="order-456",
    ... )
    >>> await logger.log(event)
"""

from __future__ import annotations

from shared.audit.base import (
    AuditAction,
    AuditEvent,
    AuditLogger,
    AuditQuery,
    InMemoryAuditLogger,
)
from shared.audit.decorator import audit_log

__all__ = [
    "AuditAction",
    "AuditEvent",
    "AuditLogger",
    "AuditQuery",
    "InMemoryAuditLogger",
    "audit_log",
]
