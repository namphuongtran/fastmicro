"""Password management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from identity_service.api.dependencies import CurrentUserIdDep, UserAuthServiceDep
from identity_service.application.schemas import (
    AuthErrorResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

router = APIRouter(prefix="/password", tags=["Password Management"])


@router.post(
    "/change",
    response_model=ChangePasswordResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid current password or policy"},
        401: {"model": AuthErrorResponse, "description": "Not authenticated"},
    },
    summary="Change password",
    description="Change password for the currently authenticated user.",
)
async def change_password(
    request: ChangePasswordRequest,
    auth_service: UserAuthServiceDep,
    user_id: CurrentUserIdDep,
) -> ChangePasswordResponse | JSONResponse:
    """Change password for authenticated user."""
    success, error = await auth_service.change_password(
        user_id=user_id,
        current_password=request.current_password,
        new_password=request.new_password,
    )

    if not success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="password_change_failed",
                error_description=error,
            ).model_dump(),
        )

    return ChangePasswordResponse()


@router.post(
    "/forgot",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Send a password reset token. Response is always success to prevent email enumeration.",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: UserAuthServiceDep,
    http_request: Request,
) -> ForgotPasswordResponse:
    """Request a password reset token."""
    ip_address = http_request.client.host if http_request.client else None

    # Always returns None or token — we ignore the return to prevent enumeration
    await auth_service.request_password_reset(
        email=str(request.email),
        ip_address=ip_address,
    )

    # TODO: In production, send email with token via notification service
    return ForgotPasswordResponse()


@router.post(
    "/reset",
    response_model=ResetPasswordResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Invalid token or password policy"},
    },
    summary="Reset password with token",
    description="Reset password using a reset token received via email.",
)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: UserAuthServiceDep,
) -> ResetPasswordResponse | JSONResponse:
    """Reset password using a reset token."""
    success, error = await auth_service.reset_password(
        token=request.token,
        new_password=request.new_password,
    )

    if not success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AuthErrorResponse(
                error="password_reset_failed",
                error_description=error,
            ).model_dump(),
        )

    return ResetPasswordResponse()
