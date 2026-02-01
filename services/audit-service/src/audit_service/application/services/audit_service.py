"""
Audit Application Service.

Implements the business logic for audit event operations, coordinating
between the API layer and the domain/infrastructure layers.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from audit_service.domain.entities.audit_event import (
    AuditEvent,
    AuditEventResponse,
    CreateAuditEventRequest,
)
from audit_service.domain.repositories.audit_repository import IAuditRepository

# Import shared library components
try:
    from shared.exceptions import NotFoundError
    from shared.observability import get_logger
except ImportError:
    import structlog

    get_logger = structlog.get_logger

    class NotFoundError(Exception):
        """Resource not found error."""

        pass


logger = get_logger(__name__)


@dataclass
class PaginatedResult:
    """Paginated result container."""

    items: list[AuditEventResponse]
    total: int


class AuditAppService:
    """
    Application service for audit event operations.

    Coordinates business logic between API controllers and domain/infrastructure.
    """

    def __init__(self, repository: IAuditRepository) -> None:
        """
        Initialize the audit application service.

        Args:
            repository: Audit event repository implementation.
        """
        self._repository = repository
        self._logger = get_logger(__name__)

    async def create_event(self, request: CreateAuditEventRequest) -> AuditEventResponse:
        """
        Create a new audit event.

        Args:
            request: Audit event creation request.

        Returns:
            AuditEventResponse: Created audit event.
        """
        # Create domain entity from request
        event = AuditEvent(
            service_name=request.service_name,
            correlation_id=request.correlation_id,
            actor_id=request.actor_id,
            actor_type=request.actor_type,
            actor_name=request.actor_name,
            actor_email=request.actor_email,
            actor_ip=request.actor_ip,
            actor_user_agent=request.actor_user_agent,
            action=request.action,
            severity=request.severity,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_name=request.resource_name,
            description=request.description,
            metadata=request.metadata,
            old_value=request.old_value,
            new_value=request.new_value,
            compliance_tags=request.compliance_tags,
        )

        # Persist the event
        created_event = await self._repository.create(event)

        self._logger.info(
            "Audit event created",
            event_id=str(created_event.id),
            action=created_event.action.value,
            actor_id=created_event.actor_id,
            resource_type=created_event.resource_type,
        )

        return self._to_response(created_event)

    async def get_event(self, event_id: UUID) -> AuditEventResponse:
        """
        Get an audit event by ID.

        Args:
            event_id: Audit event UUID.

        Returns:
            AuditEventResponse: Audit event details.

        Raises:
            NotFoundError: If event not found.
        """
        event = await self._repository.get_by_id(event_id)

        if event is None:
            raise NotFoundError(f"Audit event not found: {event_id}")

        return self._to_response(event)

    async def list_events(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Any | None = None,
    ) -> PaginatedResult:
        """
        List audit events with pagination and filtering.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Optional filter criteria.

        Returns:
            PaginatedResult: Paginated list of audit events.
        """
        # Convert filters to dict if provided
        filter_dict: dict[str, Any] | None = None
        if filters is not None:
            filter_dict = {k: v for k, v in filters.model_dump().items() if v is not None}

        events, total = await self._repository.list(
            page=page,
            page_size=page_size,
            filters=filter_dict,
        )

        return PaginatedResult(
            items=[self._to_response(e) for e in events],
            total=total,
        )

    async def search_events(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Any | None = None,
    ) -> PaginatedResult:
        """
        Search audit events using full-text search.

        Args:
            query: Search query string.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Optional additional filters.

        Returns:
            PaginatedResult: Search results.
        """
        start_date = None
        end_date = None

        if filters is not None:
            start_date = getattr(filters, "start_date", None)
            end_date = getattr(filters, "end_date", None)

        events, total = await self._repository.search(
            query=query,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
        )

        return PaginatedResult(
            items=[self._to_response(e) for e in events],
            total=total,
        )

    async def delete_event(self, event_id: UUID) -> bool:
        """
        Delete an audit event.

        Args:
            event_id: Audit event UUID.

        Returns:
            bool: True if deleted, False if not found.
        """
        deleted = await self._repository.delete_by_id(event_id)

        if deleted:
            self._logger.info("Audit event deleted", event_id=str(event_id))

        return deleted

    async def apply_retention_policy(self, retention_days: int) -> int:
        """
        Apply data retention policy by deleting old events.

        Args:
            retention_days: Number of days to retain events.

        Returns:
            int: Number of deleted events.
        """
        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
        deleted_count = await self._repository.delete_before_date(cutoff_date)

        self._logger.info(
            "Retention policy applied",
            retention_days=retention_days,
            deleted_count=deleted_count,
        )

        return deleted_count

    def _to_response(self, event: AuditEvent) -> AuditEventResponse:
        """Convert domain entity to response model."""
        return AuditEventResponse(
            id=event.id,
            timestamp=event.timestamp,
            service_name=event.service_name,
            correlation_id=event.correlation_id,
            actor_id=event.actor_id,
            actor_type=event.actor_type,
            actor_name=event.actor_name,
            action=event.action,
            severity=event.severity,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            resource_name=event.resource_name,
            description=event.description,
            compliance_tags=event.compliance_tags,
        )


# Dependency injection
_audit_service: AuditAppService | None = None


def get_audit_service() -> AuditAppService:
    """
    Get the audit application service instance.

    Uses a simple singleton pattern. In production, use proper DI container.

    Returns:
        AuditAppService: Audit application service instance.
    """
    global _audit_service

    if _audit_service is None:
        # Import repository implementation
        from audit_service.infrastructure.persistence import InMemoryAuditRepository

        repository = InMemoryAuditRepository()
        _audit_service = AuditAppService(repository)

    return _audit_service
