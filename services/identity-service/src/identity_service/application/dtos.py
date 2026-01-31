"""Application service DTOs - Data Transfer Objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuthorizationValidationResult:
    """Result of validating an authorization request."""

    is_error: bool = False
    error: str | None = None
    error_description: str | None = None
    redirect_uri: str | None = None
    client_name: str | None = None
    scopes: list[str] = field(default_factory=list)


@dataclass
class AuthorizationCodeResult:
    """Result of creating an authorization code."""

    code: str = ""
    is_error: bool = False
    error: str | None = None
    error_description: str | None = None


@dataclass
class TokenResult:
    """Result of a token request."""

    access_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 0
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None
    is_error: bool = False
    error: str | None = None
    error_description: str | None = None


@dataclass
class UserInfoResult:
    """Result of a userinfo request."""

    claims: dict[str, Any] = field(default_factory=dict)
    is_error: bool = False
    error: str | None = None
    error_description: str | None = None


@dataclass
class LoginResult:
    """Result of a login attempt."""

    success: bool = False
    user_id: uuid.UUID | None = None
    session_id: str | None = None
    error: str | None = None
    requires_mfa: bool = False
    mfa_token: str | None = None


@dataclass
class RegistrationResult:
    """Result of user registration."""

    success: bool = False
    user_id: uuid.UUID | None = None
    error: str | None = None
    errors: list[str] = field(default_factory=list)
