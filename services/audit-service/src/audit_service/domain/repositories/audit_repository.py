"""
Audit Repository interface.

Defines the abstract interface for audit event persistence operations.
Implementations can use different storage backends (PostgreSQL, MongoDB, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from audit_service.domain.entities.audit_event import AuditEvent


class IAuditRepository(ABC):
    """
    Abstract interface for audit event repository.
    
    Defines the contract for audit event persistence operations.
    Implementations should provide concrete storage mechanisms.
    """
    
    @abstractmethod
    async def create(self, event: AuditEvent) -> AuditEvent:
        """
        Create a new audit event.
        
        Args:
            event: Audit event to persist.
        
        Returns:
            AuditEvent: Created audit event with generated ID.
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> AuditEvent | None:
        """
        Get an audit event by ID.
        
        Args:
            event_id: Unique event identifier.
        
        Returns:
            AuditEvent | None: Audit event if found, None otherwise.
        """
        ...
    
    @abstractmethod
    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """
        List audit events with pagination and filtering.
        
        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Optional filter criteria.
        
        Returns:
            tuple[list[AuditEvent], int]: List of events and total count.
        """
        ...
    
    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """
        Full-text search across audit events.
        
        Args:
            query: Search query string.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
        
        Returns:
            tuple[list[AuditEvent], int]: Matching events and total count.
        """
        ...
    
    @abstractmethod
    async def delete_by_id(self, event_id: UUID) -> bool:
        """
        Delete an audit event by ID.
        
        Args:
            event_id: Unique event identifier.
        
        Returns:
            bool: True if deleted, False if not found.
        """
        ...
    
    @abstractmethod
    async def delete_before_date(self, cutoff_date: datetime) -> int:
        """
        Delete audit events older than the specified date.
        
        Used for implementing retention policies.
        
        Args:
            cutoff_date: Delete events before this date.
        
        Returns:
            int: Number of deleted events.
        """
        ...
    
    @abstractmethod
    async def count_by_actor(
        self,
        actor_id: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count audit events for a specific actor.
        
        Args:
            actor_id: Actor identifier.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
        
        Returns:
            int: Event count for the actor.
        """
        ...
    
    @abstractmethod
    async def count_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count audit events for a specific resource.
        
        Args:
            resource_type: Resource type.
            resource_id: Resource identifier.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
        
        Returns:
            int: Event count for the resource.
        """
        ...
