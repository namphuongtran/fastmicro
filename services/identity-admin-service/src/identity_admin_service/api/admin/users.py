"""Admin API routes for user management.

Provides CRUD operations for managing users.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from identity_admin_service.api.dependencies import get_user_repository
from shared.utils import now_utc

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


# ============================================================================
# Lightweight Domain Entities for Admin Service
# ============================================================================


class UserRole:
    """User role entity."""
    
    def __init__(self, user_id, role_name, expires_at=None):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.role_name = role_name
        self.assigned_at = now_utc()
        self.expires_at = expires_at
    
    def is_active(self) -> bool:
        """Check if role is currently active."""
        if self.expires_at is None:
            return True
        return now_utc() < self.expires_at


class UserProfile:
    """User profile entity."""
    
    def __init__(self, user_id):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.given_name: str | None = None
        self.family_name: str | None = None
        self.middle_name: str | None = None
        self.nickname: str | None = None
        self.preferred_username: str | None = None
        self.picture: str | None = None
        self.website: str | None = None
        self.gender: str | None = None
        self.birthdate: str | None = None
        self.zoneinfo: str | None = None
        self.locale: str | None = None
        self.phone_number: str | None = None
        self.phone_number_verified: bool = False
        self.address: str | None = None
        self.updated_at: datetime = now_utc()
    
    @property
    def full_name(self) -> str | None:
        """Get full name from given and family names."""
        parts = [p for p in [self.given_name, self.middle_name, self.family_name] if p]
        return " ".join(parts) if parts else None


class UserCredential:
    """User credential entity."""
    
    def __init__(self, user_id):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.password_hash: str | None = None
        self.last_password_change: datetime | None = None
        self.password_expires_at: datetime | None = None
        self.failed_login_attempts: int = 0
        self.locked_until: datetime | None = None
        self.mfa_enabled: bool = False
        self.mfa_secret: str | None = None
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return now_utc() < self.locked_until
    
    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts and unlock account."""
        self.failed_login_attempts = 0
        self.locked_until = None


class User:
    """User entity."""
    
    def __init__(self, email: str, username: str | None = None, email_verified: bool = False):
        self.id = uuid.uuid4()
        self.email = email
        self.username = username
        self.email_verified = email_verified
        self.is_active = True
        self.is_system = False
        self.external_id: str | None = None
        self.external_provider: str | None = None
        self.created_at = now_utc()
        self.updated_at = now_utc()
        
        # Related entities
        self.profile = UserProfile(self.id)
        self.credential = UserCredential(self.id)
        self.roles: list[UserRole] = []


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 (simplified for admin service)."""
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class UserProfileSchema(BaseModel):
    """Schema for user profile information."""

    given_name: str | None = None
    family_name: str | None = None
    middle_name: str | None = None
    nickname: str | None = None
    preferred_username: str | None = None
    picture: str | None = None
    website: str | None = None
    gender: str | None = None
    birthdate: str | None = None
    zoneinfo: str | None = None
    locale: str | None = None
    phone_number: str | None = None


class CreateUserRequest(BaseModel):
    """Request schema for creating a user."""

    email: EmailStr = Field(..., description="User's email address")
    username: str | None = Field(None, min_length=3, max_length=50, description="Optional username")
    password: str = Field(..., min_length=8, max_length=128, description="Initial password")
    email_verified: bool = Field(False, description="Whether email is pre-verified")
    profile: UserProfileSchema | None = Field(None, description="User profile information")
    roles: list[str] = Field(default=[], description="Initial roles to assign")


class UpdateUserRequest(BaseModel):
    """Request schema for updating a user."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50)
    email_verified: bool | None = None
    is_active: bool | None = None
    profile: UserProfileSchema | None = None


class UserResponse(BaseModel):
    """Response schema for user."""

    id: str
    email: str
    username: str | None
    email_verified: bool
    is_active: bool
    is_system: bool
    external_provider: str | None
    given_name: str | None
    family_name: str | None
    full_name: str | None
    picture: str | None
    phone_number: str | None
    phone_number_verified: bool
    roles: list[str]
    mfa_enabled: bool
    is_locked: bool
    failed_login_attempts: int
    created_at: str
    updated_at: str


def _user_to_response(user: User) -> UserResponse:
    """Convert user entity to response schema."""
    profile = user.profile
    credential = user.credential
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        email_verified=user.email_verified,
        is_active=user.is_active,
        is_system=user.is_system,
        external_provider=user.external_provider,
        given_name=profile.given_name if profile else None,
        family_name=profile.family_name if profile else None,
        full_name=profile.full_name if profile else None,
        picture=profile.picture if profile else None,
        phone_number=profile.phone_number if profile else None,
        phone_number_verified=profile.phone_number_verified if profile else False,
        roles=[r.role_name for r in user.roles if r.is_active()],
        mfa_enabled=credential.mfa_enabled if credential else False,
        is_locked=credential.is_locked() if credential else False,
        failed_login_attempts=credential.failed_login_attempts if credential else 0,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


class UserListResponse(BaseModel):
    """Response schema for paginated user list."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AddRoleRequest(BaseModel):
    """Request to add a role to a user."""

    role_name: str = Field(..., min_length=1, max_length=50, description="Role name to assign")
    expires_at: str | None = Field(None, description="Optional expiration date (ISO 8601)")


class ResetPasswordRequest(BaseModel):
    """Request to reset user password."""

    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    require_change: bool = Field(True, description="Require password change on next login")


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    include_inactive: bool = False,
    search: str | None = Query(None, description="Search by email or username"),
    role: str | None = Query(None, description="Filter by role"),
    user_repo=Depends(get_user_repository),
) -> UserListResponse:
    """List all users with pagination and filtering."""
    skip = (page - 1) * page_size

    # Handle role filtering separately
    if role:
        users = await user_repo.find_by_role(role)
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.email.lower() or (u.username and search_lower in u.username.lower())
            ]
        if not include_inactive:
            users = [u for u in users if u.is_active]
        total = len(users)
        users = users[skip : skip + page_size]
    elif search:
        users = await user_repo.search(
            query=search,
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = len(users) + skip
    else:
        users = await user_repo.search(
            query="",
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = await user_repo.count(include_inactive=include_inactive)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return UserListResponse(
        items=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Get a specific user by ID."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return _user_to_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Create a new user."""
    # Check for existing email
    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {request.email} already exists",
        )

    # Check for existing username
    if request.username:
        existing = await user_repo.get_by_username(request.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with username {request.username} already exists",
            )

    # Create user entity
    user = User(
        email=request.email,
        username=request.username,
        email_verified=request.email_verified,
    )

    # Set password
    user.credential.password_hash = _hash_password(request.password)
    user.credential.last_password_change = now_utc()

    # Set profile
    if request.profile:
        user.profile.given_name = request.profile.given_name
        user.profile.family_name = request.profile.family_name
        user.profile.middle_name = request.profile.middle_name
        user.profile.nickname = request.profile.nickname
        user.profile.preferred_username = request.profile.preferred_username
        user.profile.picture = request.profile.picture
        user.profile.website = request.profile.website
        user.profile.gender = request.profile.gender
        user.profile.birthdate = request.profile.birthdate
        user.profile.zoneinfo = request.profile.zoneinfo
        user.profile.locale = request.profile.locale
        user.profile.phone_number = request.profile.phone_number

    # Add roles
    for role_name in request.roles:
        user.roles.append(
            UserRole(
                user_id=user.id,
                role_name=role_name,
            )
        )

    # Persist
    created = await user_repo.create(user)
    return _user_to_response(created)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    request: UpdateUserRequest,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Update an existing user."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Check for email conflict
    if request.email and request.email != user.email:
        existing = await user_repo.get_by_email(request.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {request.email} already exists",
            )
        user.email = request.email

    # Check for username conflict
    if request.username and request.username != user.username:
        existing = await user_repo.get_by_username(request.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with username {request.username} already exists",
            )
        user.username = request.username

    if request.email_verified is not None:
        user.email_verified = request.email_verified
    if request.is_active is not None:
        user.is_active = request.is_active

    # Update profile
    if request.profile:
        p = request.profile
        if p.given_name is not None:
            user.profile.given_name = p.given_name
        if p.family_name is not None:
            user.profile.family_name = p.family_name
        if p.middle_name is not None:
            user.profile.middle_name = p.middle_name
        if p.nickname is not None:
            user.profile.nickname = p.nickname
        if p.preferred_username is not None:
            user.profile.preferred_username = p.preferred_username
        if p.picture is not None:
            user.profile.picture = p.picture
        if p.website is not None:
            user.profile.website = p.website
        if p.gender is not None:
            user.profile.gender = p.gender
        if p.birthdate is not None:
            user.profile.birthdate = p.birthdate
        if p.zoneinfo is not None:
            user.profile.zoneinfo = p.zoneinfo
        if p.locale is not None:
            user.profile.locale = p.locale
        if p.phone_number is not None:
            user.profile.phone_number = p.phone_number
        user.profile.updated_at = now_utc()

    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> None:
    """Delete (deactivate) a user."""
    deleted = await user_repo.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Activate a deactivated user."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    user.is_active = True
    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Deactivate a user."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    user.is_active = False
    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.post("/{user_id}/lock", response_model=UserResponse)
async def lock_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Lock a user account."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    if user.credential:
        # Lock for 1 year (effectively permanent until unlocked)
        user.credential.locked_until = now_utc() + timedelta(days=365)

    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.post("/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: uuid.UUID,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Unlock a locked user account."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    if user.credential:
        user.credential.reset_failed_attempts()

    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: uuid.UUID,
    request: ResetPasswordRequest,
    user_repo=Depends(get_user_repository),
) -> None:
    """Reset user password (admin action)."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    user.credential.password_hash = _hash_password(request.new_password)
    user.credential.last_password_change = now_utc()

    if request.require_change:
        # Set password as expired to force change on next login
        user.credential.password_expires_at = now_utc()

    user.credential.reset_failed_attempts()
    user.updated_at = now_utc()

    await user_repo.update(user)


@router.post("/{user_id}/roles", response_model=UserResponse)
async def add_role(
    user_id: uuid.UUID,
    request: AddRoleRequest,
    user_repo=Depends(get_user_repository),
) -> UserResponse:
    """Add a role to a user."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Check for duplicate
    existing_roles = [r.role_name for r in user.roles if r.is_active()]
    if request.role_name in existing_roles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has role: {request.role_name}",
        )

    expires_at = None
    if request.expires_at:
        expires_at = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))

    user.roles.append(
        UserRole(
            user_id=user.id,
            role_name=request.role_name,
            expires_at=expires_at,
        )
    )
    user.updated_at = now_utc()

    updated = await user_repo.update(user)
    return _user_to_response(updated)


@router.delete("/{user_id}/roles/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    user_id: uuid.UUID,
    role_name: str,
    user_repo=Depends(get_user_repository),
) -> None:
    """Remove a role from a user."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    original_count = len(user.roles)
    user.roles = [r for r in user.roles if r.role_name != role_name]

    if len(user.roles) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role not found: {role_name}",
        )

    user.updated_at = now_utc()
    await user_repo.update(user)
