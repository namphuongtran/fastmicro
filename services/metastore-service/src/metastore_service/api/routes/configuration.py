"""Configuration API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from metastore_service.api.dependencies import get_configuration_service
from metastore_service.application.dtos.configuration_dtos import (
    ConfigurationDTO,
    ConfigurationListDTO,
    ConfigurationSchemaDTO,
    ConfigurationVersionDTO,
    CreateConfigurationDTO,
    UpdateConfigurationDTO,
)
from metastore_service.application.services.configuration_service import ConfigurationService
from metastore_service.domain.value_objects import Environment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/configurations", tags=["configurations"])


@router.post(
    "",
    response_model=ConfigurationDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create configuration",
    description="Create a new configuration for a service",
)
async def create_configuration(
    dto: CreateConfigurationDTO,
    service: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationDTO:
    """Create a new configuration."""
    try:
        return await service.create(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{config_id}",
    response_model=ConfigurationDTO,
    summary="Get configuration by ID",
    description="Retrieve a configuration by its unique identifier",
)
async def get_configuration_by_id(
    config_id: UUID,
    service: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationDTO:
    """Get a configuration by ID."""
    result = await service.get_by_id(config_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
    return result


@router.get(
    "/service/{service_id}/{name}",
    response_model=ConfigurationDTO,
    summary="Get configuration by name",
    description="Retrieve a configuration by service, name, and environment",
)
async def get_configuration_by_name(
    service_id: str,
    name: str,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    environment: Environment = Query(description="The environment"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
) -> ConfigurationDTO:
    """Get a configuration by name."""
    result = await svc.get_by_name(service_id, name, environment, tenant_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found for service '{service_id}' in {environment.value}",
        )
    return result


@router.get(
    "/service/{service_id}",
    response_model=ConfigurationListDTO,
    summary="List configurations by service",
    description="List all configurations for a service",
)
async def list_configurations_by_service(
    service_id: str,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    environment: Environment | None = Query(default=None, description="Filter by environment"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    active_only: bool = Query(default=True, description="Only return active configs"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> ConfigurationListDTO:
    """List configurations by service."""
    return await svc.list_by_service(
        service_id, environment, tenant_id, active_only, limit, offset
    )


@router.get(
    "/environment/{environment}",
    response_model=ConfigurationListDTO,
    summary="List configurations by environment",
    description="List all configurations for an environment",
)
async def list_configurations_by_environment(
    environment: Environment,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    active_only: bool = Query(default=True, description="Only return active configs"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> ConfigurationListDTO:
    """List configurations by environment."""
    return await svc.list_by_environment(
        environment, tenant_id, active_only, limit, offset
    )


@router.get(
    "/search/{query}",
    response_model=ConfigurationListDTO,
    summary="Search configurations",
    description="Search configurations by name or description",
)
async def search_configurations(
    query: str,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    service_id: str | None = Query(default=None, description="Filter by service"),
    environment: Environment | None = Query(default=None, description="Filter by environment"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> ConfigurationListDTO:
    """Search configurations."""
    return await svc.search(query, service_id, environment, tenant_id, limit, offset)


@router.put(
    "/{config_id}",
    response_model=ConfigurationDTO,
    summary="Update configuration",
    description="Update an existing configuration",
)
async def update_configuration(
    config_id: UUID,
    dto: UpdateConfigurationDTO,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationDTO:
    """Update a configuration."""
    try:
        result = await svc.update(config_id, dto)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete configuration",
    description="Delete a configuration by ID",
)
async def delete_configuration(
    config_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> None:
    """Delete a configuration."""
    deleted = await svc.delete(config_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )


# Effective configuration endpoint

@router.get(
    "/effective/{service_id}",
    response_model=dict[str, Any],
    summary="Get effective configuration",
    description="Get the merged effective configuration for a service",
)
async def get_effective_configuration(
    service_id: str,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    environment: Environment = Query(description="The environment"),
    tenant_id: str | None = Query(default=None, description="The tenant ID"),
    resolve_secrets: bool = Query(default=False, description="Resolve secret references"),
) -> dict[str, Any]:
    """Get effective configuration for a service."""
    return await svc.get_effective_config(
        service_id, environment, tenant_id, resolve_secrets
    )


# Activation endpoints

@router.post(
    "/{config_id}/activate",
    response_model=ConfigurationDTO,
    summary="Activate configuration",
    description="Activate a configuration",
)
async def activate_configuration(
    config_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    updated_by: str | None = Query(default=None, description="User making the change"),
) -> ConfigurationDTO:
    """Activate a configuration."""
    result = await svc.activate(config_id, updated_by)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
    return result


@router.post(
    "/{config_id}/deactivate",
    response_model=ConfigurationDTO,
    summary="Deactivate configuration",
    description="Deactivate a configuration",
)
async def deactivate_configuration(
    config_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    updated_by: str | None = Query(default=None, description="User making the change"),
) -> ConfigurationDTO:
    """Deactivate a configuration."""
    result = await svc.deactivate(config_id, updated_by)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
    return result


# Version endpoints

@router.get(
    "/{config_id}/versions",
    response_model=list[ConfigurationVersionDTO],
    summary="Get configuration versions",
    description="Get the version history of a configuration",
)
async def get_configuration_versions(
    config_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    limit: int = Query(default=50, ge=1, le=100, description="Maximum versions"),
) -> list[ConfigurationVersionDTO]:
    """Get version history for a configuration."""
    return await svc.get_versions(config_id, limit)


@router.get(
    "/{config_id}/versions/{version_number}",
    response_model=ConfigurationVersionDTO,
    summary="Get specific version",
    description="Get a specific version of a configuration",
)
async def get_configuration_version(
    config_id: UUID,
    version_number: int,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationVersionDTO:
    """Get a specific version of a configuration."""
    result = await svc.get_version(config_id, version_number)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for configuration {config_id}",
        )
    return result


@router.post(
    "/{config_id}/rollback/{version_number}",
    response_model=ConfigurationDTO,
    summary="Rollback to version",
    description="Rollback a configuration to a specific version",
)
async def rollback_configuration(
    config_id: UUID,
    version_number: int,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    changed_by: str | None = Query(default=None, description="User making the change"),
) -> ConfigurationDTO:
    """Rollback a configuration to a specific version."""
    try:
        result = await svc.rollback(config_id, version_number, changed_by)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Schema endpoints

@router.get(
    "/schemas",
    response_model=list[ConfigurationSchemaDTO],
    summary="List schemas",
    description="List all configuration schemas",
)
async def list_schemas(
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> list[ConfigurationSchemaDTO]:
    """List all configuration schemas."""
    return await svc.list_schemas(limit, offset)


@router.post(
    "/schemas",
    response_model=ConfigurationSchemaDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create schema",
    description="Create a new configuration schema",
)
async def create_schema(
    dto: ConfigurationSchemaDTO,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationSchemaDTO:
    """Create a new configuration schema."""
    try:
        return await svc.create_schema(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/schemas/{schema_id}",
    response_model=ConfigurationSchemaDTO,
    summary="Get schema by ID",
    description="Retrieve a configuration schema by ID",
)
async def get_schema_by_id(
    schema_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> ConfigurationSchemaDTO:
    """Get a schema by ID."""
    result = await svc.get_schema_by_id(schema_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found",
        )
    return result


@router.delete(
    "/schemas/{schema_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schema",
    description="Delete a configuration schema",
)
async def delete_schema(
    schema_id: UUID,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)],
) -> None:
    """Delete a configuration schema."""
    deleted = await svc.delete_schema(schema_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found",
        )
