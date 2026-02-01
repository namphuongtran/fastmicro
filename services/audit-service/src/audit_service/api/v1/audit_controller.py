"""
Audit event endpoints for Audit Service.

Provides CRUD operations for audit events including create, list, get, search,
and export functionality.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from audit_service.application.services.audit_service import (
    AuditAppService,
    get_audit_service,
)
from audit_service.domain.entities.audit_event import (
    AuditAction,
    AuditEventResponse,
    AuditSeverity,
    CreateAuditEventRequest,
)

router = APIRouter()


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[AuditEventResponse] = Field(description="List of audit events")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    has_next: bool = Field(description="Whether there are more pages")


class SearchFilters(BaseModel):
    """Search filters for audit events."""

    actor_id: str | None = Field(default=None, description="Filter by actor ID")
    resource_type: str | None = Field(default=None, description="Filter by resource type")
    action: AuditAction | None = Field(default=None, description="Filter by action")
    severity: AuditSeverity | None = Field(default=None, description="Filter by severity")
    start_date: datetime | None = Field(default=None, description="Filter by start date")
    end_date: datetime | None = Field(default=None, description="Filter by end date")
    search_text: str | None = Field(default=None, description="Full-text search query")


@router.post(
    "/events",
    response_model=AuditEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Audit Event",
    description="Create a new audit event record",
)
async def create_audit_event(
    request: CreateAuditEventRequest,
    service: Annotated[AuditAppService, Depends(get_audit_service)],
) -> AuditEventResponse:
    """
    Create a new audit event.
    
    This endpoint records a new audit event in the system. Audit events track
    user actions, system events, and compliance-related activities.
    
    Args:
        request: Audit event creation request.
        service: Injected audit service.
    
    Returns:
        AuditEventResponse: Created audit event.
    """
    return await service.create_event(request)


@router.get(
    "/events",
    response_model=PaginatedResponse,
    summary="List Audit Events",
    description="List audit events with pagination",
)
async def list_audit_events(
    service: Annotated[AuditAppService, Depends(get_audit_service)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    actor_id: Annotated[str | None, Query(description="Filter by actor ID")] = None,
    resource_type: Annotated[str | None, Query(description="Filter by resource type")] = None,
    action: Annotated[AuditAction | None, Query(description="Filter by action")] = None,
    severity: Annotated[AuditSeverity | None, Query(description="Filter by severity")] = None,
) -> PaginatedResponse:
    """
    List audit events with optional filtering and pagination.
    
    Args:
        service: Injected audit service.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        actor_id: Optional filter by actor ID.
        resource_type: Optional filter by resource type.
        action: Optional filter by action type.
        severity: Optional filter by severity level.
    
    Returns:
        PaginatedResponse: Paginated list of audit events.
    """
    filters = SearchFilters(
        actor_id=actor_id,
        resource_type=resource_type,
        action=action,
        severity=severity,
    )

    result = await service.list_events(
        page=page,
        page_size=page_size,
        filters=filters,
    )

    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=page,
        page_size=page_size,
        has_next=result.total > page * page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=AuditEventResponse,
    summary="Get Audit Event",
    description="Get a specific audit event by ID",
)
async def get_audit_event(
    event_id: UUID,
    service: Annotated[AuditAppService, Depends(get_audit_service)],
) -> AuditEventResponse:
    """
    Get a specific audit event by ID.
    
    Args:
        event_id: Audit event UUID.
        service: Injected audit service.
    
    Returns:
        AuditEventResponse: Audit event details.
    
    Raises:
        HTTPException: If event not found (404).
    """
    return await service.get_event(event_id)


@router.get(
    "/events/search",
    response_model=PaginatedResponse,
    summary="Search Audit Events",
    description="Full-text search across audit events",
)
async def search_audit_events(
    service: Annotated[AuditAppService, Depends(get_audit_service)],
    q: Annotated[str, Query(min_length=1, description="Search query")],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    start_date: Annotated[datetime | None, Query(description="Start date filter")] = None,
    end_date: Annotated[datetime | None, Query(description="End date filter")] = None,
) -> PaginatedResponse:
    """
    Search audit events using full-text search.
    
    Args:
        service: Injected audit service.
        q: Search query string.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
    
    Returns:
        PaginatedResponse: Search results with pagination.
    """
    filters = SearchFilters(
        search_text=q,
        start_date=start_date,
        end_date=end_date,
    )

    result = await service.search_events(
        query=q,
        page=page,
        page_size=page_size,
        filters=filters,
    )

    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=page,
        page_size=page_size,
        has_next=result.total > page * page_size,
    )
