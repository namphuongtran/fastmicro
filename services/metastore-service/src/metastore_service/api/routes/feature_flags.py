"""Feature flags API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from metastore_service.api.dependencies import get_feature_flag_service
from metastore_service.application.dtos.feature_flag_dtos import (
    BulkEvaluateRequestDTO,
    BulkEvaluateResponseDTO,
    CreateFeatureFlagDTO,
    EvaluateFeatureFlagDTO,
    FeatureFlagDTO,
    FeatureFlagListDTO,
    TargetingRuleDTO,
    UpdateFeatureFlagDTO,
)
from metastore_service.application.services.feature_flag_service import FeatureFlagService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@router.post(
    "",
    response_model=FeatureFlagDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create feature flag",
    description="Create a new feature flag with optional targeting rules",
)
async def create_feature_flag(
    dto: CreateFeatureFlagDTO,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagDTO:
    """Create a new feature flag."""
    try:
        return await service.create(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{flag_id}",
    response_model=FeatureFlagDTO,
    summary="Get feature flag by ID",
    description="Retrieve a feature flag by its unique identifier",
)
async def get_feature_flag_by_id(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagDTO:
    """Get a feature flag by ID."""
    result = await service.get_by_id(flag_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found",
        )
    return result


@router.get(
    "/name/{name}",
    response_model=FeatureFlagDTO,
    summary="Get feature flag by name",
    description="Retrieve a feature flag by its unique name",
)
async def get_feature_flag_by_name(
    name: str,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagDTO:
    """Get a feature flag by name."""
    result = await service.get_by_name(name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    return result


@router.get(
    "",
    response_model=FeatureFlagListDTO,
    summary="List feature flags",
    description="List all feature flags with optional filtering",
)
async def list_feature_flags(
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    enabled_only: bool = Query(default=False, description="Only return enabled flags"),
    tags: str | None = Query(default=None, description="Comma-separated tags to filter by"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> FeatureFlagListDTO:
    """List feature flags."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return await service.list_all(enabled_only, tag_list, limit, offset)


@router.get(
    "/search/{query}",
    response_model=FeatureFlagListDTO,
    summary="Search feature flags",
    description="Search feature flags by name or description",
)
async def search_feature_flags(
    query: str,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    enabled_only: bool = Query(default=False, description="Only return enabled flags"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> FeatureFlagListDTO:
    """Search feature flags."""
    return await service.search(query, enabled_only, limit, offset)


@router.put(
    "/{flag_id}",
    response_model=FeatureFlagDTO,
    summary="Update feature flag",
    description="Update an existing feature flag",
)
async def update_feature_flag(
    flag_id: UUID,
    dto: UpdateFeatureFlagDTO,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagDTO:
    """Update a feature flag."""
    try:
        result = await service.update(flag_id, dto)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag {flag_id} not found",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{flag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete feature flag",
    description="Delete a feature flag by ID",
)
async def delete_feature_flag(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> None:
    """Delete a feature flag."""
    deleted = await service.delete(flag_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found",
        )


# Evaluation endpoints


@router.post(
    "/evaluate",
    response_model=dict[str, Any],
    summary="Evaluate feature flag",
    description="Evaluate a feature flag for a given context",
)
async def evaluate_feature_flag(
    dto: EvaluateFeatureFlagDTO,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> dict[str, Any]:
    """Evaluate a feature flag."""
    try:
        result = await service.evaluate(
            dto.name,
            dto.context,
            dto.tenant_id,
            dto.environment,
        )
        return {"name": dto.name, "value": result, "enabled": result is not None}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/evaluate/bulk",
    response_model=BulkEvaluateResponseDTO,
    summary="Bulk evaluate feature flags",
    description="Evaluate multiple feature flags at once",
)
async def bulk_evaluate_feature_flags(
    dto: BulkEvaluateRequestDTO,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> BulkEvaluateResponseDTO:
    """Bulk evaluate feature flags."""
    return await service.bulk_evaluate(dto)


# Enable/Disable endpoints


@router.post(
    "/{flag_id}/enable",
    response_model=FeatureFlagDTO,
    summary="Enable feature flag",
    description="Enable a feature flag",
)
async def enable_feature_flag(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    updated_by: str | None = Query(default=None, description="User making the change"),
) -> FeatureFlagDTO:
    """Enable a feature flag."""
    result = await service.enable(flag_id, updated_by)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found",
        )
    return result


@router.post(
    "/{flag_id}/disable",
    response_model=FeatureFlagDTO,
    summary="Disable feature flag",
    description="Disable a feature flag",
)
async def disable_feature_flag(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    updated_by: str | None = Query(default=None, description="User making the change"),
) -> FeatureFlagDTO:
    """Disable a feature flag."""
    result = await service.disable(flag_id, updated_by)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found",
        )
    return result


# Rollout percentage endpoint


@router.post(
    "/{flag_id}/rollout",
    response_model=FeatureFlagDTO,
    summary="Set rollout percentage",
    description="Set the rollout percentage for a feature flag",
)
async def set_rollout_percentage(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    percentage: int = Query(ge=0, le=100, description="Rollout percentage (0-100)"),
    updated_by: str | None = Query(default=None, description="User making the change"),
) -> FeatureFlagDTO:
    """Set the rollout percentage for a feature flag."""
    result = await service.set_rollout_percentage(flag_id, percentage, updated_by)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found",
        )
    return result


# Targeting rules endpoints


@router.get(
    "/{flag_id}/rules",
    response_model=list[TargetingRuleDTO],
    summary="Get targeting rules",
    description="Get all targeting rules for a feature flag",
)
async def get_targeting_rules(
    flag_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> list[TargetingRuleDTO]:
    """Get targeting rules for a feature flag."""
    return await service.get_targeting_rules(flag_id)


@router.post(
    "/{flag_id}/rules",
    response_model=TargetingRuleDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add targeting rule",
    description="Add a targeting rule to a feature flag",
)
async def add_targeting_rule(
    flag_id: UUID,
    rule: TargetingRuleDTO,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> TargetingRuleDTO:
    """Add a targeting rule to a feature flag."""
    try:
        return await service.add_targeting_rule(flag_id, rule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{flag_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove targeting rule",
    description="Remove a targeting rule from a feature flag",
)
async def remove_targeting_rule(
    flag_id: UUID,
    rule_id: UUID,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> None:
    """Remove a targeting rule from a feature flag."""
    removed = await service.remove_targeting_rule(flag_id, rule_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Targeting rule {rule_id} not found for feature flag {flag_id}",
        )
