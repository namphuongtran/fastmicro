"""
In-memory audit repository implementation.

Provides a simple in-memory storage for development and testing.
Should be replaced with SQLAlchemy implementation for production.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from audit_service.domain.entities.audit_event import AuditEvent
from audit_service.domain.repositories.audit_repository import IAuditRepository


class InMemoryAuditRepository(IAuditRepository):
    """
    In-memory implementation of audit repository.

    Stores audit events in memory. Suitable for development and testing only.
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        self._events: dict[UUID, AuditEvent] = {}

    async def create(self, event: AuditEvent) -> AuditEvent:
        """Create a new audit event."""
        self._events[event.id] = event
        return event

    async def get_by_id(self, event_id: UUID) -> AuditEvent | None:
        """Get an audit event by ID."""
        return self._events.get(event_id)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """List audit events with pagination and filtering."""
        events = list(self._events.values())

        # Apply filters
        if filters:
            if actor_id := filters.get("actor_id"):
                events = [e for e in events if e.actor_id == actor_id]
            if resource_type := filters.get("resource_type"):
                events = [e for e in events if e.resource_type == resource_type]
            if action := filters.get("action"):
                events = [e for e in events if e.action == action]
            if severity := filters.get("severity"):
                events = [e for e in events if e.severity == severity]

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)

        total = len(events)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = events[start:end]

        return paginated, total

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """Full-text search across audit events."""
        query_lower = query.lower()
        events = []

        for event in self._events.values():
            # Simple text search across relevant fields
            searchable = " ".join(
                [
                    event.actor_id,
                    event.actor_name or "",
                    event.resource_type,
                    event.resource_id,
                    event.resource_name or "",
                    event.description or "",
                    event.action.value,
                ]
            ).lower()

            if query_lower in searchable:
                # Apply date filters
                if start_date and event.timestamp < start_date:
                    continue
                if end_date and event.timestamp > end_date:
                    continue
                events.append(event)

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)

        total = len(events)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = events[start_idx:end_idx]

        return paginated, total

    async def delete_by_id(self, event_id: UUID) -> bool:
        """Delete an audit event by ID."""
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False

    async def delete_before_date(self, cutoff_date: datetime) -> int:
        """Delete audit events older than the specified date."""
        to_delete = [
            event_id for event_id, event in self._events.items() if event.timestamp < cutoff_date
        ]

        for event_id in to_delete:
            del self._events[event_id]

        return len(to_delete)

    async def count_by_actor(
        self,
        actor_id: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count audit events for a specific actor."""
        count = 0
        for event in self._events.values():
            if event.actor_id != actor_id:
                continue
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            count += 1
        return count

    async def count_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count audit events for a specific resource."""
        count = 0
        for event in self._events.values():
            if event.resource_type != resource_type:
                continue
            if event.resource_id != resource_id:
                continue
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            count += 1
        return count
