"""User DTOs — request/response models for the API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUserRequest(BaseModel):
    """Request DTO for creating a new user."""

    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    first_name: str = Field(default="", max_length=255)
    last_name: str = Field(default="", max_length=255)
    tenant_id: str | None = None


class UpdateUserRequest(BaseModel):
    """Request DTO for updating an existing user."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    """Response DTO for user data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    first_name: str
    last_name: str
    tenant_id: str | None
    is_active: bool
    preferences: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None


class UserListResponse(BaseModel):
    """Paginated list response."""

    items: list[UserResponse]
    total: int
    offset: int
    limit: int
