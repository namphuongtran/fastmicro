"""Metadata API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from metastore_service.api.dependencies import get_metadata_service
from metastore_service.application.dtos.metadata_dtos import (
    CreateMetadataDTO,
    MetadataDTO,
    MetadataListDTO,
    MetadataVersionDTO,
    UpdateMetadataDTO,
)
from metastore_service.application.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.post(
    "",
    response_model=MetadataDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create metadata entry",
    description="Create a new metadata entry with optional namespace and tags",
)
async def create_metadata(
    dto: CreateMetadataDTO,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MetadataDTO:
    """Create a new metadata entry."""
    try:
        return await service.create(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{metadata_id}",
    response_model=MetadataDTO,
    summary="Get metadata by ID",
    description="Retrieve a metadata entry by its unique identifier",
)
async def get_metadata_by_id(
    metadata_id: UUID,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MetadataDTO:
    """Get a metadata entry by ID."""
    result = await service.get_by_id(metadata_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata entry {metadata_id} not found",
        )
    return result


@router.get(
    "/key/{key}",
    response_model=MetadataDTO,
    summary="Get metadata by key",
    description="Retrieve a metadata entry by its key, namespace, and tenant",
)
async def get_metadata_by_key(
    key: str,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    namespace: str | None = Query(default="default", description="The namespace"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
) -> MetadataDTO:
    """Get a metadata entry by key."""
    result = await service.get_by_key(key, namespace, tenant_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata entry '{key}' not found in namespace '{namespace}'",
        )
    return result


@router.get(
    "",
    response_model=MetadataListDTO,
    summary="List metadata entries",
    description="List metadata entries in a namespace with optional filtering",
)
async def list_metadata(
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    namespace: str = Query(default="default", description="The namespace"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> MetadataListDTO:
    """List metadata entries in a namespace."""
    return await service.list_by_namespace(namespace, tenant_id, limit, offset)


@router.get(
    "/tags/{tags}",
    response_model=MetadataListDTO,
    summary="List metadata by tags",
    description="List metadata entries that have any of the specified tags",
)
async def list_metadata_by_tags(
    tags: str,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> MetadataListDTO:
    """List metadata entries by tags."""
    tag_list = [t.strip() for t in tags.split(",")]
    return await service.list_by_tags(tag_list, tenant_id, limit, offset)


@router.get(
    "/search/{query}",
    response_model=MetadataListDTO,
    summary="Search metadata",
    description="Search metadata entries by key pattern or description",
)
async def search_metadata(
    query: str,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    namespace: str | None = Query(default=None, description="The namespace to search in"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> MetadataListDTO:
    """Search metadata entries."""
    return await service.search(query, namespace, tenant_id, limit, offset)


@router.put(
    "/{metadata_id}",
    response_model=MetadataDTO,
    summary="Update metadata",
    description="Update an existing metadata entry",
)
async def update_metadata(
    metadata_id: UUID,
    dto: UpdateMetadataDTO,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MetadataDTO:
    """Update a metadata entry."""
    try:
        result = await service.update(metadata_id, dto)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata entry {metadata_id} not found",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{metadata_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete metadata",
    description="Delete a metadata entry by ID",
)
async def delete_metadata(
    metadata_id: UUID,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> None:
    """Delete a metadata entry."""
    deleted = await service.delete(metadata_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata entry {metadata_id} not found",
        )


@router.get(
    "/{metadata_id}/versions",
    response_model=list[MetadataVersionDTO],
    summary="Get metadata versions",
    description="Get the version history of a metadata entry",
)
async def get_metadata_versions(
    metadata_id: UUID,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    limit: int = Query(default=50, ge=1, le=100, description="Maximum versions to return"),
) -> list[MetadataVersionDTO]:
    """Get version history for a metadata entry."""
    return await service.get_versions(metadata_id, limit)


@router.get(
    "/{metadata_id}/versions/{version_number}",
    response_model=MetadataVersionDTO,
    summary="Get specific version",
    description="Get a specific version of a metadata entry",
)
async def get_metadata_version(
    metadata_id: UUID,
    version_number: int,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MetadataVersionDTO:
    """Get a specific version of a metadata entry."""
    result = await service.get_version(metadata_id, version_number)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for metadata {metadata_id}",
        )
    return result


@router.post(
    "/{metadata_id}/rollback/{version_number}",
    response_model=MetadataDTO,
    summary="Rollback to version",
    description="Rollback a metadata entry to a specific version",
)
async def rollback_metadata(
    metadata_id: UUID,
    version_number: int,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    changed_by: str | None = Query(default=None, description="User making the change"),
) -> MetadataDTO:
    """Rollback a metadata entry to a specific version."""
    try:
        result = await service.rollback(metadata_id, version_number, changed_by)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata entry {metadata_id} not found",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
