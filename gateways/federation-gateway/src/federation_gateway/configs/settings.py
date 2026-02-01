"""Federation Gateway settings configuration.

This module provides gateway-specific settings that extend
the shared configuration module.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.config import (
    CORSSettings,
    CryptoSettings,
    SessionSettings,
    get_settings,
)


class OIDCSettings(BaseSettings):
    """OIDC provider configuration.

    Attributes:
        issuer_url: OIDC issuer URL.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        redirect_uri: OAuth2 redirect URI.
        scopes: OAuth2 scopes to request.
    """

    model_config = SettingsConfigDict(
        env_prefix="OIDC_",
        extra="ignore",
        case_sensitive=False,
    )

    issuer_url: str = Field(
        default="",
        description="OIDC issuer URL",
    )
    client_id: str = Field(
        default="",
        description="OAuth2 client ID",
    )
    client_secret: SecretStr | None = Field(
        default=None,
        description="OAuth2 client secret",
    )
    redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        description="OAuth2 redirect URI",
    )
    scopes: str = Field(
        default="openid profile email",
        description="OAuth2 scopes to request",
    )


class GatewayAuthSettings(BaseSettings):
    """Gateway authentication settings.

    Combines OIDC settings with shared auth settings.

    Attributes:
        oidc: OIDC provider settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        extra="ignore",
        case_sensitive=False,
    )

    oidc: OIDCSettings = Field(
        default_factory=OIDCSettings,
        description="OIDC provider settings",
    )


class GatewaySecuritySettings(BaseSettings):
    """Gateway security settings.

    Provides access to security components (CORS, session, crypto).

    Attributes:
        cors: CORS middleware settings.
        session: Session middleware settings.
        crypto: Cryptographic settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        extra="ignore",
        case_sensitive=False,
    )

    cors: CORSSettings = Field(
        default_factory=CORSSettings,
        description="CORS middleware settings",
    )
    session: SessionSettings = Field(
        default_factory=SessionSettings,
        description="Session middleware settings",
    )
    crypto: CryptoSettings = Field(
        default_factory=CryptoSettings,
        description="Cryptographic settings",
    )


class FederationGatewaySettings(BaseSettings):
    """Federation Gateway application settings.

    Central configuration for the federation gateway service.

    Attributes:
        jwt_secret: Secret key for JWT token signing.
        jwt_algorithm: JWT signing algorithm.
        token_expire_minutes: Access token expiration time.
        auth: Authentication settings including OIDC.
        security: Security settings (CORS, session, crypto).

    Example:
        >>> settings = get_settings()
        >>> print(settings.jwt_algorithm)
        HS256
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # JWT settings
    jwt_secret: SecretStr = Field(
        default=SecretStr("change-this-secret-in-production"),
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token expiration in minutes",
    )

    # Nested settings
    auth: GatewayAuthSettings = Field(
        default_factory=GatewayAuthSettings,
        description="Authentication settings",
    )
    security: GatewaySecuritySettings = Field(
        default_factory=GatewaySecuritySettings,
        description="Security settings",
    )


@lru_cache
def get_settings() -> FederationGatewaySettings:
    """Get cached application settings singleton.

    Returns:
        FederationGatewaySettings instance.
    """
    return FederationGatewaySettings()
