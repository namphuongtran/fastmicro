"""Authentication configuration settings.

This module provides authentication and authorization settings
for JWT tokens, OAuth2, and API key authentication.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Authentication and authorization settings.

    Provides configuration for JWT tokens, OAuth2 scopes,
    and API key authentication.

    Attributes:
        secret_key: Secret key for signing tokens.
        algorithm: JWT signing algorithm (HS256, RS256, etc.).
        access_token_expire_minutes: Access token lifetime.
        refresh_token_expire_days: Refresh token lifetime.
        token_url: OAuth2 token endpoint URL.
        scopes: Available OAuth2 scopes.
        issuer: JWT issuer claim.
        audience: JWT audience claim.
        password_min_length: Minimum password length.
        api_key_header: Header name for API key authentication.

    Example:
        >>> settings = AuthSettings()
        >>> print(settings.algorithm)
        HS256
    """

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # JWT settings
    secret_key: SecretStr = Field(
        ...,
        description="Secret key for signing JWT tokens",
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token expiration in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="Refresh token expiration in days",
    )

    # OAuth2 settings
    token_url: str = Field(
        default="/token",
        description="OAuth2 token endpoint URL",
    )
    scopes: dict[str, str] = Field(
        default={
            "read": "Read access",
            "write": "Write access",
            "admin": "Admin access",
        },
        description="Available OAuth2 scopes",
    )

    # JWT claims
    issuer: str | None = Field(
        default=None,
        description="JWT issuer claim (iss)",
    )
    audience: str | None = Field(
        default=None,
        description="JWT audience claim (aud)",
    )

    # Password policy
    password_min_length: int = Field(
        default=8,
        ge=6,
        description="Minimum password length",
    )

    # API key authentication
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication",
    )
