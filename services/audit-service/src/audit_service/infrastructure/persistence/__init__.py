"""Infrastructure persistence layer for Audit Service."""

from audit_service.infrastructure.persistence.in_memory_repository import (
    InMemoryAuditRepository,
)

__all__ = ["InMemoryAuditRepository"]
