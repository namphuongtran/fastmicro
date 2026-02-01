"""Token Introspection and Revocation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from pydantic import BaseModel

from identity_service.api.dependencies import OAuth2ServiceDep

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


class IntrospectionResponse(BaseModel):
    """Token introspection response (RFC 7662)."""

    active: bool
    scope: str | None = None
    client_id: str | None = None
    username: str | None = None
    token_type: str | None = None
    exp: int | None = None
    iat: int | None = None
    nbf: int | None = None
    sub: str | None = None
    aud: str | list[str] | None = None
    iss: str | None = None
    jti: str | None = None


@router.post("/introspect", response_model=IntrospectionResponse)
async def introspect_token(
    request: Request,
    token: Annotated[str, Form()],
    oauth2_service: OAuth2ServiceDep,
    token_type_hint: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> IntrospectionResponse:
    """Token Introspection endpoint (RFC 7662).

    Allows resource servers to validate tokens and get their metadata.

    Args:
        request: HTTP request
        token: Token to introspect
        token_type_hint: Hint about token type (access_token, refresh_token)
        client_id: Client identifier
        client_secret: Client secret
        authorization: HTTP Basic Auth header

    Returns:
        Token metadata if active, otherwise {"active": false}.
    """
    # Authenticate client
    auth_client_id = client_id
    auth_client_secret = client_secret

    if authorization and authorization.startswith("Basic "):
        import base64

        try:
            credentials = base64.b64decode(authorization[6:]).decode("utf-8")
            auth_client_id, auth_client_secret = credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client"},
            ) from None

    if not auth_client_id or not auth_client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Client authentication required",
            },
        )

    # Verify client credentials
    is_valid_client = await oauth2_service.verify_client(auth_client_id, auth_client_secret)
    if not is_valid_client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_client"},
        )

    # Introspect the token
    result = await oauth2_service.introspect_token(token, token_type_hint)

    return IntrospectionResponse(**result.to_dict())


class RevocationResponse(BaseModel):
    """Token revocation response."""

    pass  # RFC 7009 specifies empty 200 response on success


@router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke_token(
    request: Request,
    token: Annotated[str, Form()],
    oauth2_service: OAuth2ServiceDep,
    token_type_hint: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Token Revocation endpoint (RFC 7009).

    Allows clients to revoke access or refresh tokens.

    Args:
        request: HTTP request
        token: Token to revoke
        token_type_hint: Hint about token type
        client_id: Client identifier
        client_secret: Client secret
        authorization: HTTP Basic Auth header

    Returns:
        Empty 200 response on success.
    """
    # Authenticate client
    auth_client_id = client_id
    auth_client_secret = client_secret

    if authorization and authorization.startswith("Basic "):
        import base64

        try:
            credentials = base64.b64decode(authorization[6:]).decode("utf-8")
            auth_client_id, auth_client_secret = credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client"},
            ) from None

    if not auth_client_id or not auth_client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Client authentication required",
            },
        )

    # Verify client credentials
    is_valid_client = await oauth2_service.verify_client(auth_client_id, auth_client_secret)
    if not is_valid_client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_client"},
        )

    # Revoke the token
    await oauth2_service.revoke_token(token, auth_client_id, token_type_hint)

    # RFC 7009: Return 200 OK even if token was invalid
    return None
