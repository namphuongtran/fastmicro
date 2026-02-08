"""User registration endpoint."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from identity_service.api.dependencies import UserAuthServiceDep
from identity_service.application.schemas import (
    AuthErrorResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": AuthErrorResponse, "description": "Email or username already exists"},
        422: {"model": AuthErrorResponse, "description": "Validation error"},
    },
    summary="Register a new user",
    description="Create a new user account with email, password, and optional profile details.",
)
async def register(
    request: RegisterRequest,
    auth_service: UserAuthServiceDep,
) -> RegisterResponse | JSONResponse:
    """Register a new user account."""
    result = await auth_service.register(
        email=str(request.email),
        password=request.password,
        username=request.username,
        given_name=request.given_name,
        family_name=request.family_name,
    )

    if not result.success:
        status_code = status.HTTP_409_CONFLICT
        if result.error == "weak_password":
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        return JSONResponse(
            status_code=status_code,
            content={
                "error": result.error or "registration_failed",
                "error_description": "; ".join(result.errors) if result.errors else None,
            },
        )

    return RegisterResponse(
        user_id=result.user_id,
        email=str(request.email),
        username=request.username,
    )
