"""JWT token management for authentication.

This module provides JWT token creation and verification services
following enterprise security best practices.

Example:
    >>> from shared.auth.jwt import JWTService, TokenType
    >>> jwt_service = JWTService(secret_key="your-secret-key")
    >>> token = jwt_service.create_access_token(
    ...     subject="user_123",
    ...     scopes=["read", "write"],
    ... )
    >>> token_data = jwt_service.verify_token(token)
    >>> print(token_data.sub)
    'user_123'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import InvalidTokenError as JWTInvalidToken


class TokenType(str, Enum):
    """Token types for JWT authentication.

    Attributes:
        ACCESS: Short-lived token for API access.
        REFRESH: Long-lived token for obtaining new access tokens.
    """

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenData:
    """Data contained in a JWT token.

    Attributes:
        sub: The subject identifier (usually user ID).
        exp: When the token expires.
        iat: When the token was issued.
        token_type: Type of the token (access or refresh).
        scopes: List of permission scopes.
        custom_claims: Additional custom claims.
        iss: Token issuer (optional).
        aud: Token audience (optional).
    """

    sub: str
    exp: datetime
    iat: datetime
    token_type: TokenType = TokenType.ACCESS
    scopes: list[str] = field(default_factory=list)
    custom_claims: dict[str, Any] = field(default_factory=dict)
    iss: str | None = None
    aud: str | None = None

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope.

        Args:
            scope: The scope to check.

        Returns:
            True if the token has the scope.
        """
        return scope in self.scopes

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired.

        Returns:
            True if the token is expired.
        """
        return datetime.now(UTC) > self.exp


class InvalidTokenError(Exception):
    """Raised when a token is invalid or malformed.

    This exception is raised when token verification fails
    due to invalid signature, malformed payload, or other issues.
    """

    pass


class ExpiredTokenError(InvalidTokenError):
    """Raised when a token has expired.

    This exception is specifically for expired tokens, allowing
    different handling than other token validation errors.
    Inherits from InvalidTokenError for easier catching.
    """

    pass


class JWTService:
    """Service for creating and verifying JWT tokens.

    This service handles JWT token operations following security best practices:
    - Uses strong algorithms (HS256 by default, supports RS256)
    - Includes standard claims (iat, exp, sub)
    - Supports custom claims and scopes
    - Validates token expiration and signature

    Attributes:
        secret_key: Secret key for signing tokens.
        algorithm: JWT algorithm (default: HS256).
        access_token_expire_minutes: Access token expiry in minutes.
        refresh_token_expire_days: Refresh token expiry in days.
        issuer: Token issuer claim.
        audience: Token audience claim.

    Example:
        >>> service = JWTService(secret_key="secret")
        >>> token = service.create_access_token("user_123")
        >>> data = service.verify_token(token)
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        """Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens.
            algorithm: JWT algorithm (HS256, RS256, etc.).
            access_token_expire_minutes: Access token expiry in minutes.
            refresh_token_expire_days: Refresh token expiry in days.
            issuer: Token issuer (iss claim).
            audience: Token audience (aud claim).
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

    def create_access_token(
        self,
        subject: str,
        scopes: list[str] | None = None,
        custom_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create an access token.

        Args:
            subject: The subject identifier (usually user ID).
            scopes: List of permission scopes.
            custom_claims: Additional claims to include.
            expires_delta: Custom expiration delta.

        Returns:
            Encoded JWT access token string.

        Example:
            >>> token = service.create_access_token(
            ...     subject="user_123",
            ...     scopes=["read", "write"],
            ... )
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        return self._create_token(
            subject=subject,
            token_type=TokenType.ACCESS,
            scopes=scopes or [],
            custom_claims=custom_claims or {},
            expires_delta=expires_delta,
        )

    def create_refresh_token(
        self,
        subject: str,
        custom_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a refresh token.

        Args:
            subject: The subject identifier (usually user ID).
            custom_claims: Additional claims to include.
            expires_delta: Custom expiration delta.

        Returns:
            Encoded JWT refresh token string.

        Example:
            >>> refresh_token = service.create_refresh_token("user_123")
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        return self._create_token(
            subject=subject,
            token_type=TokenType.REFRESH,
            scopes=[],
            custom_claims=custom_claims or {},
            expires_delta=expires_delta,
        )

    def verify_token(
        self,
        token: str,
        expected_type: TokenType | None = None,
    ) -> TokenData:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token string.
            expected_type: Expected token type (optional).

        Returns:
            TokenData containing the decoded token information.

        Raises:
            InvalidTokenError: If the token is invalid or malformed.
            ExpiredTokenError: If the token has expired.

        Example:
            >>> token_data = service.verify_token(token)
            >>> print(token_data.sub)
        """
        try:
            # Build decode options
            decode_kwargs: dict[str, Any] = {
                "algorithms": [self.algorithm],
            }

            if self.audience:
                decode_kwargs["audience"] = self.audience
            if self.issuer:
                decode_kwargs["issuer"] = self.issuer

            payload = jwt.decode(
                token,
                self.secret_key,
                **decode_kwargs,
            )

            # Extract token data
            token_type_str = payload.get("type", TokenType.ACCESS.value)
            token_type = TokenType(token_type_str)

            # Validate expected type if specified
            if expected_type is not None and token_type != expected_type:
                raise InvalidTokenError(
                    f"Expected {expected_type.value} token, got {token_type.value}"
                )

            # Parse timestamps
            iat = payload.get("iat")
            exp = payload.get("exp")

            issued_at = (
                datetime.fromtimestamp(iat, tz=UTC) if iat is not None else datetime.now(UTC)
            )
            expires_at = (
                datetime.fromtimestamp(exp, tz=UTC) if exp is not None else datetime.now(UTC)
            )

            # Extract scopes and custom claims
            scopes = payload.get("scopes", [])

            # Standard claims to exclude from custom_claims
            standard_claims = {"sub", "iat", "exp", "type", "scopes", "iss", "aud"}
            custom_claims = {k: v for k, v in payload.items() if k not in standard_claims}

            return TokenData(
                sub=payload["sub"],
                exp=expires_at,
                iat=issued_at,
                token_type=token_type,
                scopes=scopes,
                custom_claims=custom_claims,
                iss=payload.get("iss"),
                aud=payload.get("aud"),
            )

        except ExpiredSignatureError as e:
            raise ExpiredTokenError("Token has expired") from e
        except JWTInvalidToken as e:
            raise InvalidTokenError(f"Invalid token: {e}") from e
        except (KeyError, ValueError) as e:
            raise InvalidTokenError(f"Malformed token payload: {e}") from e

    def decode_token(self, token: str, verify: bool = True) -> TokenData:
        """Decode a token with optional verification.

        Args:
            token: The JWT token string.
            verify: Whether to verify the signature (default: True).

        Returns:
            TokenData containing the decoded token information.

        Raises:
            InvalidTokenError: If the token cannot be decoded.
        """
        if verify:
            return self.verify_token(token)

        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )

            # Parse timestamps
            iat = payload.get("iat")
            exp = payload.get("exp")

            issued_at = (
                datetime.fromtimestamp(iat, tz=UTC) if iat is not None else datetime.now(UTC)
            )
            expires_at = (
                datetime.fromtimestamp(exp, tz=UTC) if exp is not None else datetime.now(UTC)
            )

            # Extract token type
            token_type_str = payload.get("type", TokenType.ACCESS.value)
            token_type = TokenType(token_type_str)

            # Extract scopes and custom claims
            scopes = payload.get("scopes", [])
            standard_claims = {"sub", "iat", "exp", "type", "scopes", "iss", "aud"}
            custom_claims = {k: v for k, v in payload.items() if k not in standard_claims}

            return TokenData(
                sub=payload["sub"],
                exp=expires_at,
                iat=issued_at,
                token_type=token_type,
                scopes=scopes,
                custom_claims=custom_claims,
                iss=payload.get("iss"),
                aud=payload.get("aud"),
            )
        except JWTInvalidToken as e:
            raise InvalidTokenError(f"Cannot decode token: {e}") from e
        except (KeyError, ValueError) as e:
            raise InvalidTokenError(f"Malformed token payload: {e}") from e

    def _create_token(
        self,
        subject: str,
        token_type: TokenType,
        scopes: list[str],
        custom_claims: dict[str, Any],
        expires_delta: timedelta,
    ) -> str:
        """Create a JWT token with the given parameters.

        Args:
            subject: The subject identifier.
            token_type: Type of token (access/refresh).
            scopes: List of permission scopes.
            custom_claims: Additional claims.
            expires_delta: Expiration delta from now.

        Returns:
            Encoded JWT token string.
        """
        now = datetime.now(UTC)
        expire = now + expires_delta

        payload: dict[str, Any] = {
            "sub": subject,
            "type": token_type.value,
            "scopes": scopes,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            **custom_claims,
        }

        # Add optional claims
        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


__all__ = [
    "ExpiredTokenError",
    "InvalidTokenError",
    "JWTService",
    "TokenData",
    "TokenType",
]
