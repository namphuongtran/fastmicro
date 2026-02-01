"""OAuth2 Token endpoint - /oauth2/token."""

from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from pydantic import BaseModel

from identity_service.api.dependencies import OAuth2ServiceDep
from identity_service.api.oauth.device import (
    check_polling_rate,
    consume_device_code,
    get_device_code_entry,
)

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


class TokenErrorResponse(BaseModel):
    """OAuth2 error response."""

    error: str
    error_description: str | None = None
    error_uri: str | None = None


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        400: {"model": TokenErrorResponse, "description": "Invalid request"},
        401: {"model": TokenErrorResponse, "description": "Invalid client"},
    },
)
async def token_endpoint(
    request: Request,
    grant_type: Annotated[str, Form()],
    oauth2_service: OAuth2ServiceDep,
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    device_code: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    """OAuth2 Token endpoint.

    Exchanges authorization codes for tokens or refreshes tokens.

    Supports:
    - authorization_code: Exchange code for tokens
    - client_credentials: Machine-to-machine tokens
    - refresh_token: Refresh access tokens
    - urn:ietf:params:oauth:grant-type:device_code: Device authorization (RFC 8628)

    Args:
        request: HTTP request
        grant_type: OAuth2 grant type
        code: Authorization code (for authorization_code grant)
        redirect_uri: Redirect URI (must match authorization request)
        client_id: Client identifier (if not using HTTP Basic Auth)
        client_secret: Client secret (if not using HTTP Basic Auth)
        code_verifier: PKCE code verifier
        refresh_token: Refresh token (for refresh_token grant)
        scope: Requested scope
        device_code: Device code (for device_code grant)
        authorization: HTTP Basic Auth header

    Returns:
        Token response with access_token, etc.
    """
    # Parse Basic Auth if provided
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
                detail={"error": "invalid_client", "error_description": "Invalid credentials"},
            ) from None

    # Process token request based on grant type
    if grant_type == "authorization_code":
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_request", "error_description": "Missing code parameter"},
            )

        result = await oauth2_service.exchange_code(
            code=code,
            client_id=auth_client_id,
            client_secret=auth_client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

    elif grant_type == "client_credentials":
        if not auth_client_id or not auth_client_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_client",
                    "error_description": "Client authentication required",
                },
            )

        result = await oauth2_service.client_credentials(
            client_id=auth_client_id,
            client_secret=auth_client_secret,
            scope=scope,
        )

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_request",
                    "error_description": "Missing refresh_token parameter",
                },
            )

        result = await oauth2_service.refresh_token(
            refresh_token=refresh_token,
            client_id=auth_client_id,
            client_secret=auth_client_secret,
            scope=scope,
        )

    elif grant_type == "urn:ietf:params:oauth:grant-type:device_code":
        # RFC 8628 Device Authorization Grant
        if not device_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_request",
                    "error_description": "Missing device_code parameter",
                },
            )

        if not auth_client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_client",
                    "error_description": "Client identifier required",
                },
            )

        # Get device code entry
        entry = get_device_code_entry(device_code)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_grant",
                    "error_description": "Invalid or expired device code",
                },
            )

        # Verify client matches
        if entry.client_id != auth_client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_grant",
                    "error_description": "Device code was not issued to this client",
                },
            )

        # Check polling rate (RFC 8628 Section 3.5)
        if not check_polling_rate(device_code, entry.interval):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "slow_down",
                    "error_description": "Polling too frequently, please wait",
                },
            )

        # Check if user denied
        if entry.denied:
            consume_device_code(device_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "access_denied",
                    "error_description": "User denied the authorization request",
                },
            )

        # Check if not yet authorized
        if not entry.authorized or not entry.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "authorization_pending",
                    "error_description": "User has not yet completed authorization",
                },
            )

        # Device code is authorized - issue tokens
        consumed_entry = consume_device_code(device_code)
        if not consumed_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_grant",
                    "error_description": "Device code already used or expired",
                },
            )

        # Issue tokens for the authorized user
        result = await oauth2_service.issue_tokens_for_user(
            user_id=consumed_entry.user_id,
            client_id=auth_client_id,
            scope=consumed_entry.scope,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "unsupported_grant_type",
                "error_description": f"Grant type '{grant_type}' not supported",
            },
        )

    if result.is_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": result.error, "error_description": result.error_description},
        )

    return TokenResponse(
        access_token=result.access_token,
        token_type="Bearer",
        expires_in=result.expires_in,
        refresh_token=result.refresh_token,
        scope=result.scope,
        id_token=result.id_token,
    )
