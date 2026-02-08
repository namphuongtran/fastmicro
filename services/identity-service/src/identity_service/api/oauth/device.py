"""OAuth2 Device Authorization endpoint - RFC 8628.

This module implements the Device Authorization Grant flow for
input-constrained devices (CLI tools, IoT devices, smart TVs).

Flow:
1. Device requests authorization at /oauth2/device_authorization
2. User visits verification_uri and enters user_code
3. Device polls /oauth2/token with device_code until authorized
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Request, status
from pydantic import BaseModel

from identity_service.api.dependencies import OAuth2ServiceDep
from identity_service.configs import get_settings
from shared.observability import get_structlog_logger

logger = get_structlog_logger(__name__)

router = APIRouter(prefix="/oauth2", tags=["oauth2-device"])


# ========================================
# Response Models
# ========================================


class DeviceAuthorizationResponse(BaseModel):
    """Device authorization response per RFC 8628 Section 3.2."""

    device_code: str
    """The device verification code."""

    user_code: str
    """The end-user verification code (e.g., "WDJB-MJHT")."""

    verification_uri: str
    """The end-user verification URI."""

    verification_uri_complete: str | None = None
    """Optional URI that includes the user_code."""

    expires_in: int
    """Lifetime in seconds of the device_code and user_code."""

    interval: int = 5
    """Minimum polling interval in seconds."""


class DeviceAuthorizationErrorResponse(BaseModel):
    """Device authorization error response."""

    error: str
    error_description: str | None = None


# ========================================
# In-Memory Device Code Storage (Replace with Redis in production)
# ========================================


class DeviceCodeEntry:
    """Device code storage entry."""

    def __init__(
        self,
        device_code: str,
        user_code: str,
        client_id: str,
        scope: str | None,
        expires_at: datetime,
        interval: int = 5,
    ):
        self.device_code = device_code
        self.user_code = user_code
        self.client_id = client_id
        self.scope = scope
        self.expires_at = expires_at
        self.interval = interval
        self.last_polled_at: datetime | None = None
        self.authorized: bool = False
        self.denied: bool = False
        self.user_id: str | None = None
        self.authorized_at: datetime | None = None


# In-memory storage (use Redis/database in production)
_device_codes: dict[str, DeviceCodeEntry] = {}
_user_codes: dict[str, str] = {}  # user_code -> device_code mapping


def _generate_user_code(length: int = 8) -> str:
    """Generate human-friendly user code.

    Format: XXXX-XXXX (alphanumeric, easy to type)
    Excludes confusing characters: 0, O, 1, I, L
    """
    import random

    # Characters that are easy to read and type
    chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    code = "".join(random.choices(chars, k=length))
    return f"{code[:4]}-{code[4:]}"


def _cleanup_expired_codes() -> None:
    """Remove expired device codes."""
    now = datetime.now(UTC)
    expired = [dc for dc, entry in _device_codes.items() if entry.expires_at < now]
    for dc in expired:
        entry = _device_codes.pop(dc, None)
        if entry:
            _user_codes.pop(entry.user_code, None)


# ========================================
# Device Authorization Endpoint
# ========================================


@router.post(
    "/device_authorization",
    response_model=DeviceAuthorizationResponse,
    responses={
        400: {"model": DeviceAuthorizationErrorResponse},
        401: {"model": DeviceAuthorizationErrorResponse},
    },
    summary="Device Authorization Request",
    description="Initiate device authorization flow (RFC 8628)",
)
async def device_authorization(
    request: Request,
    oauth2_service: OAuth2ServiceDep,
    client_id: Annotated[str, Form()],
    scope: Annotated[str | None, Form()] = None,
) -> DeviceAuthorizationResponse:
    """Device authorization endpoint per RFC 8628 Section 3.1.

    Called by input-constrained devices to start the authorization flow.

    Args:
        request: HTTP request
        client_id: OAuth2 client identifier
        scope: Requested scopes (space-separated)

    Returns:
        Device authorization response with codes and URIs
    """
    settings = get_settings()

    # Cleanup expired codes periodically
    _cleanup_expired_codes()

    # Validate client
    client = await oauth2_service.get_client(client_id)
    if not client:
        logger.warning("Device auth: invalid client", client_id=client_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Unknown or invalid client",
            },
        )

    # Validate client supports device flow
    if "urn:ietf:params:oauth:grant-type:device_code" not in client.grant_types:
        logger.warning(
            "Device auth: grant type not allowed",
            client_id=client_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "unauthorized_client",
                "error_description": "Client not authorized for device authorization grant",
            },
        )

    # Validate requested scopes
    if scope:
        requested_scopes = set(scope.split())
        allowed_scopes = set(client.scopes)
        invalid_scopes = requested_scopes - allowed_scopes
        if invalid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_scope",
                    "error_description": f"Invalid scopes: {', '.join(invalid_scopes)}",
                },
            )

    # Generate codes
    device_code = str(uuid4())
    user_code = _generate_user_code()

    # Ensure unique user code
    while user_code in _user_codes:
        user_code = _generate_user_code()

    # Calculate expiration (default 15 minutes)
    expires_in = getattr(settings, "device_code_lifetime", 900)
    expires_at = datetime.now(UTC).replace(microsecond=0) + __import__("datetime").timedelta(
        seconds=expires_in
    )

    # Store device code
    entry = DeviceCodeEntry(
        device_code=device_code,
        user_code=user_code,
        client_id=client_id,
        scope=scope,
        expires_at=expires_at,
    )
    _device_codes[device_code] = entry
    _user_codes[user_code] = device_code

    # Build verification URIs
    base_url = str(request.base_url).rstrip("/")
    verification_uri = f"{base_url}/device"
    verification_uri_complete = f"{verification_uri}?user_code={user_code}"

    logger.info(
        "Device authorization initiated",
        client_id=client_id,
        user_code=user_code,
        expires_in=expires_in,
    )

    return DeviceAuthorizationResponse(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        verification_uri_complete=verification_uri_complete,
        expires_in=expires_in,
        interval=5,
    )


# ========================================
# Device Verification Functions (for token endpoint)
# ========================================


def get_device_code_entry(device_code: str) -> DeviceCodeEntry | None:
    """Get device code entry for validation."""
    _cleanup_expired_codes()
    return _device_codes.get(device_code)


def authorize_device_code(
    user_code: str,
    user_id: str,
) -> bool:
    """Authorize a device code after user verification.

    Called when user approves the device on the verification page.

    Args:
        user_code: The user verification code
        user_id: The authenticated user's ID

    Returns:
        True if authorization succeeded
    """
    _cleanup_expired_codes()

    device_code = _user_codes.get(user_code)
    if not device_code:
        return False

    entry = _device_codes.get(device_code)
    if not entry:
        return False

    if entry.expires_at < datetime.now(UTC):
        return False

    entry.authorized = True
    entry.user_id = user_id
    entry.authorized_at = datetime.now(UTC)

    logger.info(
        "Device code authorized",
        user_code=user_code,
        user_id=user_id,
    )

    return True


def deny_device_code(user_code: str) -> bool:
    """Deny a device code after user rejection.

    Args:
        user_code: The user verification code

    Returns:
        True if denial was recorded
    """
    device_code = _user_codes.get(user_code)
    if not device_code:
        return False

    entry = _device_codes.get(device_code)
    if not entry:
        return False

    entry.denied = True

    logger.info("Device code denied", user_code=user_code)

    return True


def consume_device_code(device_code: str) -> DeviceCodeEntry | None:
    """Consume and remove a device code after token exchange.

    Args:
        device_code: The device verification code

    Returns:
        The entry if valid and authorized, None otherwise
    """
    entry = _device_codes.pop(device_code, None)
    if entry:
        _user_codes.pop(entry.user_code, None)
    return entry


def check_polling_rate(device_code: str, interval: int = 5) -> bool:
    """Check if device is polling too fast.

    Args:
        device_code: The device verification code
        interval: Minimum seconds between polls

    Returns:
        True if polling rate is OK, False if too fast (slow_down)
    """
    entry = _device_codes.get(device_code)
    if not entry:
        return True

    now = datetime.now(UTC)
    if entry.last_polled_at:
        elapsed = (now - entry.last_polled_at).total_seconds()
        if elapsed < interval:
            return False

    entry.last_polled_at = now
    return True
