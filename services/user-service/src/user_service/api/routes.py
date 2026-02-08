"""User API routes — CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from user_service.api.dependencies import ServiceContextDep, UserServiceDep
from user_service.application.dtos import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    body: CreateUserRequest,
    service: UserServiceDep,
    ctx: ServiceContextDep,
) -> UserResponse:
    """Create a new user account."""
    return await service.create_user(body, context=ctx)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
)
async def get_user(
    user_id: str,
    service: UserServiceDep,
    ctx: ServiceContextDep,
) -> UserResponse:
    """Retrieve a user by their unique identifier."""
    return await service.get_user(user_id, context=ctx)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    service: UserServiceDep,
    ctx: ServiceContextDep,
) -> UserResponse:
    """Partially update a user's profile."""
    return await service.update_user(user_id, body, context=ctx)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate a user",
)
async def deactivate_user(
    user_id: str,
    service: UserServiceDep,
    ctx: ServiceContextDep,
) -> UserResponse:
    """Deactivate a user account (soft delete)."""
    return await service.deactivate_user(user_id, context=ctx)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
async def delete_user(
    user_id: str,
    service: UserServiceDep,
    ctx: ServiceContextDep,
) -> None:
    """Permanently delete a user."""
    await service.delete_user(user_id, context=ctx)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
)
async def list_users(
    service: UserServiceDep,
    ctx: ServiceContextDep,
    tenant_id: str | None = Query(default=None, description="Filter by tenant"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> UserListResponse:
    """List users with pagination, optionally filtered by tenant."""
    return await service.list_users(
        tenant_id=tenant_id,
        offset=offset,
        limit=limit,
        context=ctx,
    )
