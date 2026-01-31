"""UserInfo endpoint - /oauth2/userinfo."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from identity_service.api.dependencies import OAuth2ServiceDep

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


class UserInfoResponse(BaseModel):
    """OIDC UserInfo response."""

    model_config = ConfigDict(extra="allow")  # Allow additional claims

    sub: str
    name: str | None = None
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
    email: str | None = None
    email_verified: bool | None = None
    phone_number: str | None = None
    phone_number_verified: bool | None = None
    address: dict | None = None
    updated_at: int | None = None


@router.get("/userinfo", response_model=UserInfoResponse)
@router.post("/userinfo", response_model=UserInfoResponse)
async def userinfo_endpoint(
    request: Request,
    oauth2_service: OAuth2ServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> UserInfoResponse:
    """OIDC UserInfo endpoint.

    Returns claims about the authenticated user based on the
    scopes granted in the access token.

    Requires Bearer token authentication.

    Args:
        request: HTTP request
        authorization: Bearer token header

    Returns:
        User claims dictionary.
    """
    # Extract bearer token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail={"error": "invalid_token", "error_description": "Missing or invalid authorization header"},
        )

    access_token = authorization[7:]  # Remove "Bearer " prefix

    # Validate token and get user claims
    result = await oauth2_service.get_userinfo(access_token)

    if result.is_error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": f'Bearer error="{result.error}"'},
            detail={"error": result.error, "error_description": result.error_description},
        )

    return UserInfoResponse(**result.claims)
