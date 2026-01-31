"""
Unit tests for Audit Application Service.
"""

import pytest
from uuid import uuid4

from audit_service.application.services.audit_service import (
    AuditAppService,
    PaginatedResult,
)
from audit_service.domain.entities.audit_event import (
    AuditAction,
    AuditSeverity,
    CreateAuditEventRequest,
)
from audit_service.infrastructure.persistence.in_memory_repository import (
    InMemoryAuditRepository,
)


@pytest.fixture
def repository() -> InMemoryAuditRepository:
    """Create a fresh in-memory repository for each test."""
    return InMemoryAuditRepository()


@pytest.fixture
def service(repository: InMemoryAuditRepository) -> AuditAppService:
    """Create audit service with repository."""
    return AuditAppService(repository)


@pytest.fixture
def sample_request() -> CreateAuditEventRequest:
    """Create a sample audit event request."""
    return CreateAuditEventRequest(
        service_name="test-service",
        actor_id="user-123",
        actor_type="user",
        actor_name="Test User",
        action=AuditAction.CREATE,
        severity=AuditSeverity.INFO,
        resource_type="document",
        resource_id="doc-456",
        resource_name="Test Document",
        description="Created a new document",
    )


class TestAuditAppService:
    """Tests for AuditAppService."""
    
    @pytest.mark.asyncio
    async def test_create_event(
        self,
        service: AuditAppService,
        sample_request: CreateAuditEventRequest,
    ) -> None:
        """Test creating an audit event."""
        response = await service.create_event(sample_request)
        
        assert response.id is not None
        assert response.actor_id == sample_request.actor_id
        assert response.action == sample_request.action
        assert response.resource_type == sample_request.resource_type
        assert response.resource_id == sample_request.resource_id
    
    @pytest.mark.asyncio
    async def test_get_event(
        self,
        service: AuditAppService,
        sample_request: CreateAuditEventRequest,
    ) -> None:
        """Test getting an audit event by ID."""
        created = await service.create_event(sample_request)
        retrieved = await service.get_event(created.id)
        
        assert retrieved.id == created.id
        assert retrieved.actor_id == created.actor_id
    
    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self,
        service: AuditAppService,
    ) -> None:
        """Test getting a non-existent event raises error."""
        with pytest.raises(Exception):  # NotFoundError
            await service.get_event(uuid4())
    
    @pytest.mark.asyncio
    async def test_list_events_empty(
        self,
        service: AuditAppService,
    ) -> None:
        """Test listing events when repository is empty."""
        result = await service.list_events()
        
        assert isinstance(result, PaginatedResult)
        assert result.items == []
        assert result.total == 0
    
    @pytest.mark.asyncio
    async def test_list_events_with_data(
        self,
        service: AuditAppService,
        sample_request: CreateAuditEventRequest,
    ) -> None:
        """Test listing events with data."""
        # Create multiple events
        for i in range(5):
            request = sample_request.model_copy(
                update={"resource_id": f"doc-{i}"}
            )
            await service.create_event(request)
        
        result = await service.list_events(page=1, page_size=3)
        
        assert len(result.items) == 3
        assert result.total == 5
    
    @pytest.mark.asyncio
    async def test_list_events_pagination(
        self,
        service: AuditAppService,
        sample_request: CreateAuditEventRequest,
    ) -> None:
        """Test pagination of events."""
        # Create 10 events
        for i in range(10):
            request = sample_request.model_copy(
                update={"resource_id": f"doc-{i}"}
            )
            await service.create_event(request)
        
        # Get page 1
        page1 = await service.list_events(page=1, page_size=3)
        assert len(page1.items) == 3
        
        # Get page 2
        page2 = await service.list_events(page=2, page_size=3)
        assert len(page2.items) == 3
        
        # Ensure different items
        page1_ids = {item.id for item in page1.items}
        page2_ids = {item.id for item in page2.items}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_delete_event(
        self,
        service: AuditAppService,
        sample_request: CreateAuditEventRequest,
    ) -> None:
        """Test deleting an audit event."""
        created = await service.create_event(sample_request)
        
        deleted = await service.delete_event(created.id)
        assert deleted is True
        
        # Verify it's gone
        with pytest.raises(Exception):
            await service.get_event(created.id)
    
    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self,
        service: AuditAppService,
    ) -> None:
        """Test deleting a non-existent event returns False."""
        deleted = await service.delete_event(uuid4())
        assert deleted is False
