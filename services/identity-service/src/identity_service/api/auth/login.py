"""User login endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from identity_service.api.dependencies import UserAuthServiceDep
from identity_service.application.schemas import (
    AuthErrorResponse,
    LoginRequest,
    LoginResponse,
    MFARequiredResponse,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        200: {"model": LoginResponse, "description": "Successful login"},
        202: {"model": MFARequiredResponse, "description": "MFA verification required"},
        401: {"model": AuthErrorResponse, "description": "Invalid credentials"},
        423: {"model": AuthErrorResponse, "description": "Account locked"},
        429: {"model": AuthErrorResponse, "description": "Too many attempts"},
    },
    summary="Authenticate user",
    description="Login with email and password. May return MFA challenge if enabled.",
)
async def login(
    request: LoginRequest,
    auth_service: UserAuthServiceDep,
    http_request: Request,
) -> LoginResponse | MFARequiredResponse | JSONResponse:
    """Authenticate user with email and password."""
    # Extract client info
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    result = await auth_service.login(
        email=str(request.email),
        password=request.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if result.requires_mfa:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=MFARequiredResponse(
                mfa_token=result.mfa_token or "",
            ).model_dump(),
        )

    if not result.success:
        error_status_map = {
            "account_locked": status.HTTP_423_LOCKED,
            "ip_blocked": status.HTTP_429_TOO_MANY_REQUESTS,
            "too_many_attempts": status.HTTP_429_TOO_MANY_REQUESTS,
            "invalid_credentials": status.HTTP_401_UNAUTHORIZED,
            "login_disabled": status.HTTP_403_FORBIDDEN,
        }
        status_code = error_status_map.get(result.error or "", status.HTTP_401_UNAUTHORIZED)

        return JSONResponse(
            status_code=status_code,
            content={
                "error": result.error or "authentication_failed",
                "error_description": _error_description(result.error),
            },
        )

    return LoginResponse(
        access_token="",  # Token is generated internally; extend as needed
        expires_in=3600,
        session_id=result.session_id,
    )


def _error_description(error: str | None) -> str:
    """Map error codes to user-friendly descriptions."""
    descriptions = {
        "account_locked": "Account is temporarily locked due to too many failed attempts",
        "ip_blocked": "Too many failed login attempts from this IP address",
        "too_many_attempts": "Please wait before trying again",
        "invalid_credentials": "Invalid email or password",
        "login_disabled": "This account has been deactivated",
    }
    return descriptions.get(error or "", "Authentication failed")
