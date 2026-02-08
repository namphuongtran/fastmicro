"""MFA (Multi-Factor Authentication) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from identity_service.api.dependencies import (
    CurrentUserIdDep,
    MFAServiceDep,
    UserAuthServiceDep,
)
from identity_service.application.schemas import (
    AuthErrorResponse,
    MFADisableRequest,
    MFADisableResponse,
    MFALoginVerifyResponse,
    MFARecoveryRequest,
    MFARecoveryResponse,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
)

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])


# =========================================================================
# Setup
# =========================================================================


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "MFA already enabled"},
        401: {"model": AuthErrorResponse, "description": "Not authenticated"},
    },
    summary="Initiate MFA setup",
    description="Generate TOTP secret and recovery codes. MFA is not enabled until verified.",
)
async def setup_mfa(
    mfa_service: MFAServiceDep,
    user_id: CurrentUserIdDep,
) -> MFASetupResponse | JSONResponse:
    """Initiate MFA setup for authenticated user."""
    secret, provisioning_uri, recovery_codes = await mfa_service.setup_mfa(user_id)

    if secret is None or provisioning_uri is None or recovery_codes is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="mfa_setup_failed",
                error_description="MFA is already enabled or user not found",
            ).model_dump(),
        )

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        recovery_codes=recovery_codes,
    )


# =========================================================================
# Verify (Setup Confirmation)
# =========================================================================


@router.post(
    "/verify",
    response_model=MFAVerifyResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid code or MFA not initiated"},
    },
    summary="Verify TOTP and enable MFA",
    description="Confirm authenticator setup by verifying a code. Enables MFA on success.",
)
async def verify_mfa_setup(
    request: MFAVerifyRequest,
    mfa_service: MFAServiceDep,
    user_id: CurrentUserIdDep,
) -> MFAVerifyResponse | JSONResponse:
    """Verify TOTP code to complete MFA setup."""
    success, error = await mfa_service.verify_and_enable(user_id, request.code)

    if not success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="mfa_verification_failed",
                error_description=error,
            ).model_dump(),
        )

    return MFAVerifyResponse()


# =========================================================================
# Verify Login (MFA step during login)
# =========================================================================


@router.post(
    "/verify-login",
    response_model=MFALoginVerifyResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Invalid code or token"},
    },
    summary="Complete login with MFA",
    description="Verify TOTP code to complete the login flow after receiving an MFA challenge.",
)
async def verify_mfa_login(
    request: MFAVerifyRequest,
    mfa_service: MFAServiceDep,
    auth_service: UserAuthServiceDep,
) -> MFALoginVerifyResponse | JSONResponse:
    """Verify TOTP code during login to complete authentication."""
    if not request.mfa_token:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="missing_mfa_token",
                error_description="mfa_token is required for login verification",
            ).model_dump(),
        )

    user_id, error = await mfa_service.verify_login_code(
        mfa_token=request.mfa_token,
        code=request.code,
    )

    if user_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=AuthErrorResponse(
                error="mfa_verification_failed",
                error_description=error,
            ).model_dump(),
        )

    # Complete login — MFA passed
    # Return a placeholder response; full token generation happens via _complete_login
    return MFALoginVerifyResponse(
        access_token="",
        expires_in=3600,
        session_id=None,
    )


# =========================================================================
# Recovery Code
# =========================================================================


@router.post(
    "/recovery",
    response_model=MFARecoveryResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Invalid recovery code or token"},
    },
    summary="Login with recovery code",
    description="Use a one-time recovery code to complete MFA login when authenticator is unavailable.",
)
async def use_recovery_code(
    request: MFARecoveryRequest,
    mfa_service: MFAServiceDep,
) -> MFARecoveryResponse | JSONResponse:
    """Use a recovery code to bypass TOTP during login."""
    user_id, remaining, error = await mfa_service.verify_recovery_code(
        mfa_token=request.mfa_token,
        recovery_code=request.recovery_code,
    )

    if user_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=AuthErrorResponse(
                error="recovery_failed",
                error_description=error,
            ).model_dump(),
        )

    return MFARecoveryResponse(
        access_token="",
        expires_in=3600,
        remaining_recovery_codes=remaining,
    )


# =========================================================================
# Disable
# =========================================================================


@router.post(
    "/disable",
    response_model=MFADisableResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid password or code"},
        401: {"model": AuthErrorResponse, "description": "Not authenticated"},
    },
    summary="Disable MFA",
    description="Disable MFA for the authenticated user. Requires password and current TOTP.",
)
async def disable_mfa(
    request: MFADisableRequest,
    mfa_service: MFAServiceDep,
    user_id: CurrentUserIdDep,
) -> MFADisableResponse | JSONResponse:
    """Disable MFA for authenticated user."""
    success, error = await mfa_service.disable_mfa(
        user_id=user_id,
        password=request.password,
        code=request.code,
    )

    if not success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="mfa_disable_failed",
                error_description=error,
            ).model_dump(),
        )

    return MFADisableResponse()


# =========================================================================
# Status
# =========================================================================


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Not authenticated"},
    },
    summary="Get MFA status",
    description="Check if MFA is enabled and how many recovery codes remain.",
)
async def get_mfa_status(
    mfa_service: MFAServiceDep,
    user_id: CurrentUserIdDep,
) -> MFAStatusResponse:
    """Get MFA status for authenticated user."""
    enabled, remaining = await mfa_service.get_mfa_status(user_id)

    return MFAStatusResponse(
        mfa_enabled=enabled,
        recovery_codes_remaining=remaining,
    )
