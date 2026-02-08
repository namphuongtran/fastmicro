"""Request/Response schemas for auth endpoints.

Pydantic models for API request validation and response serialization.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# Registration
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=12, max_length=128, description="User password")
    username: str | None = Field(
        default=None, min_length=3, max_length=50, description="Optional username"
    )
    given_name: str | None = Field(default=None, max_length=100, description="First name")
    family_name: str | None = Field(default=None, max_length=100, description="Last name")

    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterResponse(BaseModel):
    """User registration response."""

    user_id: uuid.UUID
    email: str
    username: str | None = None
    message: str = "Registration successful"


# =============================================================================
# Login
# =============================================================================


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(description="User password")

    model_config = ConfigDict(str_strip_whitespace=True)


class LoginResponse(BaseModel):
    """Successful login response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None
    session_id: str | None = None


class MFARequiredResponse(BaseModel):
    """Response when MFA verification is required."""

    requires_mfa: bool = True
    mfa_token: str = Field(description="Temporary token for MFA verification")
    message: str = "MFA verification required"


# =============================================================================
# Password Management
# =============================================================================


class ChangePasswordRequest(BaseModel):
    """Change password request (authenticated user)."""

    current_password: str = Field(description="Current password")
    new_password: str = Field(min_length=12, max_length=128, description="New password")


class ChangePasswordResponse(BaseModel):
    """Change password response."""

    message: str = "Password changed successfully"
    password_expires_at: datetime | None = None


class ForgotPasswordRequest(BaseModel):
    """Forgot password request (unauthenticated)."""

    email: EmailStr = Field(description="Email address for password reset")

    model_config = ConfigDict(str_strip_whitespace=True)


class ForgotPasswordResponse(BaseModel):
    """Forgot password response.

    Always returns success to prevent email enumeration.
    """

    message: str = "If an account with that email exists, a reset link has been sent"


class ResetPasswordRequest(BaseModel):
    """Reset password with token."""

    token: str = Field(description="Password reset token")
    new_password: str = Field(min_length=12, max_length=128, description="New password")


class ResetPasswordResponse(BaseModel):
    """Reset password response."""

    message: str = "Password reset successfully"


# =============================================================================
# MFA
# =============================================================================


class MFASetupResponse(BaseModel):
    """MFA setup initiation response."""

    secret: str = Field(description="TOTP secret (base32 encoded)")
    provisioning_uri: str = Field(description="otpauth:// URI for QR code generation")
    recovery_codes: list[str] = Field(description="One-time recovery codes")
    message: str = "Scan the QR code with your authenticator app, then verify"


class MFAVerifyRequest(BaseModel):
    """MFA verification request (for both setup confirmation and login)."""

    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit TOTP")
    mfa_token: str | None = Field(
        default=None, description="MFA token from login (required for login verification)"
    )


class MFAVerifyResponse(BaseModel):
    """MFA verification response."""

    verified: bool = True
    message: str = "MFA verification successful"


class MFALoginVerifyResponse(BaseModel):
    """MFA login verification response (returns tokens after MFA step)."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None
    session_id: str | None = None


class MFADisableRequest(BaseModel):
    """MFA disable request (requires password confirmation)."""

    password: str = Field(description="Current password for confirmation")
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", description="Current TOTP")


class MFADisableResponse(BaseModel):
    """MFA disable response."""

    message: str = "MFA has been disabled"


class MFARecoveryRequest(BaseModel):
    """MFA recovery code verification request."""

    recovery_code: str = Field(description="One-time recovery code")
    mfa_token: str = Field(description="MFA token from login")


class MFARecoveryResponse(BaseModel):
    """MFA recovery response (returns tokens after recovery code)."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    remaining_recovery_codes: int = Field(description="Number of recovery codes remaining")


class MFAStatusResponse(BaseModel):
    """MFA status response."""

    mfa_enabled: bool
    recovery_codes_remaining: int = 0


# =============================================================================
# Shared Error Response
# =============================================================================


class AuthErrorResponse(BaseModel):
    """Standard auth error response."""

    error: str
    error_description: str | None = None
