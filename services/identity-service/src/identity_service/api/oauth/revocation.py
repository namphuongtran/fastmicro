"""OAuth2 Token Revocation endpoint - RFC 7009.

This module implements token revocation for access and refresh tokens.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Response, status
from pydantic import BaseModel

from identity_service.api.dependencies import OAuth2ServiceDep
from shared.observability import get_structlog_logger

logger = get_structlog_logger(__name__)

router = APIRouter(prefix="/oauth2", tags=["oauth2-revocation"])


# ========================================
# In-Memory Revoked Tokens Storage (Replace with Redis in production)
# ========================================

# Set of revoked token JTIs (JWT ID) or token hashes
_revoked_tokens: set[str] = set()
_revoked_refresh_tokens: dict[str, datetime] = {}  # token -> revoked_at


def revoke_token(token_id: str, token_type: str = "access_token") -> None:
    """Add token to revocation list.

    Args:
        token_id: Token JTI or hash
        token_type: Type of token being revoked
    """
    if token_type == "refresh_token":
        _revoked_refresh_tokens[token_id] = datetime.now(UTC)
    else:
        _revoked_tokens.add(token_id)

    logger.info("Token revoked", token_type=token_type)


def is_token_revoked(token_id: str) -> bool:
    """Check if token has been revoked.

    Args:
        token_id: Token JTI or hash

    Returns:
        True if token is revoked
    """
    return token_id in _revoked_tokens or token_id in _revoked_refresh_tokens


def cleanup_expired_revocations(max_age_hours: int = 24) -> int:
    """Clean up old revocation entries.

    Args:
        max_age_hours: Maximum age of revocation entries to keep

    Returns:
        Number of entries cleaned up
    """
    cutoff = datetime.now(UTC) - __import__("datetime").timedelta(hours=max_age_hours)
    expired = [t for t, revoked_at in _revoked_refresh_tokens.items() if revoked_at < cutoff]
    for token in expired:
        _revoked_refresh_tokens.pop(token, None)
    return len(expired)


# ========================================
# Response Models
# ========================================


class RevocationErrorResponse(BaseModel):
    """Token revocation error response."""

    error: str
    error_description: str | None = None


# ========================================
# Token Revocation Endpoint
# ========================================


@router.post(
    "/revoke",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": RevocationErrorResponse},
        401: {"model": RevocationErrorResponse},
    },
    summary="Revoke Token",
    description="Revoke an access or refresh token (RFC 7009)",
)
async def revoke_endpoint(
    oauth2_service: OAuth2ServiceDep,
    token: Annotated[str, Form()],
    token_type_hint: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Token revocation endpoint per RFC 7009.

    Revokes access tokens or refresh tokens. The authorization server
    responds with HTTP 200 whether or not the token was successfully
    revoked (to prevent token scanning).

    Args:
        token: The token to revoke
        token_type_hint: Optional hint about token type ("access_token" or "refresh_token")
        client_id: Client identifier (if not using HTTP Basic Auth)
        client_secret: Client secret (if not using HTTP Basic Auth)
        authorization: HTTP Basic Auth header

    Returns:
        Empty 200 response on success
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

    # Validate client (confidential clients must authenticate)
    if auth_client_id:
        client = await oauth2_service.get_client(auth_client_id)
        if not client:
            # Per RFC 7009, invalid client returns 401
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_client", "error_description": "Unknown client"},
            )

        # Verify client secret for confidential clients
        if client.client_type == "confidential":
            if not auth_client_secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_client",
                        "error_description": "Client authentication required",
                    },
                )

            if not await oauth2_service.verify_client_secret(auth_client_id, auth_client_secret):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_client",
                        "error_description": "Invalid client credentials",
                    },
                )

    # Attempt to revoke the token
    # Per RFC 7009, we return 200 regardless of whether revocation succeeded
    # to prevent token scanning attacks
    try:
        # Try to decode/validate the token to get its ID
        token_type = token_type_hint or "access_token"

        if token_type == "refresh_token":
            # Revoke refresh token
            token_id = await oauth2_service.get_refresh_token_id(token)
            if token_id:
                revoke_token(token_id, "refresh_token")
                # Also revoke associated access tokens
                await oauth2_service.revoke_tokens_for_refresh_token(token)
        else:
            # Revoke access token
            token_info = await oauth2_service.decode_access_token(token)
            if token_info and token_info.get("jti"):
                revoke_token(token_info["jti"], "access_token")

        logger.info(
            "Token revocation processed",
            token_type=token_type,
            client_id=auth_client_id,
        )

    except Exception as e:
        # Log but don't expose errors (per RFC 7009 security considerations)
        logger.debug("Token revocation error (suppressed)", error=str(e))

    # Always return 200 OK (RFC 7009 Section 2.2)
    return Response(status_code=status.HTTP_200_OK)


# ========================================
# Token Revocation Check (for resource servers)
# ========================================


@router.post(
    "/revocation_check",
    summary="Check Token Revocation",
    description="Check if a token has been revoked (internal use)",
    include_in_schema=False,  # Internal endpoint
)
async def check_revocation(
    token_id: Annotated[str, Form()],
) -> dict:
    """Check if a token ID has been revoked.

    This is an internal endpoint for resource servers to check
    token revocation status.

    Args:
        token_id: Token JTI to check

    Returns:
        Revocation status
    """
    return {
        "revoked": is_token_revoked(token_id),
        "checked_at": datetime.now(UTC).isoformat(),
    }
