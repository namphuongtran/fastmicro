"""Security configuration settings.

This module provides comprehensive security settings including
CORS, rate limiting, security headers, and cryptographic options.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SameSitePolicy(str, Enum):
    """Cookie SameSite policy options."""

    STRICT = "strict"
    LAX = "lax"
    NONE = "none"


class CORSSettings(BaseSettings):
    """Cross-Origin Resource Sharing (CORS) settings.

    Attributes:
        enabled: Enable CORS middleware.
        allow_origins: Allowed origins (use ["*"] for all).
        allow_methods: Allowed HTTP methods.
        allow_headers: Allowed headers.
        expose_headers: Headers exposed to the browser.
        allow_credentials: Allow credentials (cookies, auth headers).
        max_age: Preflight request cache duration.
    """

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable CORS middleware")
    allow_origins: list[str] = Field(
        default=["*"],
        description="Allowed origins",
    )
    allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed headers",
    )
    expose_headers: list[str] = Field(
        default=[],
        description="Headers exposed to the browser",
    )
    allow_credentials: bool = Field(
        default=False,
        description="Allow credentials",
    )
    max_age: int = Field(
        default=600,
        ge=0,
        description="Preflight cache duration in seconds",
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration.

    Attributes:
        enabled: Enable rate limiting.
        requests_per_minute: Maximum requests per minute per client.
        requests_per_hour: Maximum requests per hour per client.
        burst_size: Maximum burst size.
        key_prefix: Redis key prefix for rate limit data.
        whitelist: IP addresses or API keys to exempt.
    """

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable rate limiting")
    requests_per_minute: int = Field(
        default=60,
        ge=1,
        description="Max requests per minute",
    )
    requests_per_hour: int = Field(
        default=1000,
        ge=1,
        description="Max requests per hour",
    )
    burst_size: int = Field(
        default=10,
        ge=1,
        description="Maximum burst size",
    )
    key_prefix: str = Field(
        default="rate_limit:",
        description="Redis key prefix",
    )
    whitelist: list[str] = Field(
        default=[],
        description="Exempt IPs or API keys",
    )


class SecurityHeadersSettings(BaseSettings):
    """Security HTTP headers configuration.

    Attributes:
        enabled: Enable security headers middleware.
        content_security_policy: Content-Security-Policy header value.
        strict_transport_security: HSTS header value.
        x_content_type_options: X-Content-Type-Options header.
        x_frame_options: X-Frame-Options header.
        x_xss_protection: X-XSS-Protection header.
        referrer_policy: Referrer-Policy header.
        permissions_policy: Permissions-Policy header.
    """

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_HEADERS_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable security headers")
    content_security_policy: str | None = Field(
        default="default-src 'self'",
        description="Content-Security-Policy header",
    )
    strict_transport_security: str = Field(
        default="max-age=31536000; includeSubDomains",
        description="HSTS header",
    )
    x_content_type_options: str = Field(
        default="nosniff",
        description="X-Content-Type-Options header",
    )
    x_frame_options: str = Field(
        default="DENY",
        description="X-Frame-Options header",
    )
    x_xss_protection: str = Field(
        default="1; mode=block",
        description="X-XSS-Protection header",
    )
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        description="Referrer-Policy header",
    )
    permissions_policy: str | None = Field(
        default=None,
        description="Permissions-Policy header",
    )


class CookieSettings(BaseSettings):
    """Cookie security settings.

    Attributes:
        secure: Require HTTPS for cookies.
        http_only: Prevent JavaScript access to cookies.
        same_site: SameSite cookie policy.
        domain: Cookie domain.
        path: Cookie path.
    """

    model_config = SettingsConfigDict(
        env_prefix="COOKIE_",
        extra="ignore",
        case_sensitive=False,
    )

    secure: bool = Field(default=True, description="Require HTTPS for cookies")
    http_only: bool = Field(
        default=True,
        description="Prevent JavaScript access to cookies",
    )
    same_site: SameSitePolicy = Field(
        default=SameSitePolicy.LAX,
        description="SameSite cookie policy",
    )
    domain: str | None = Field(default=None, description="Cookie domain")
    path: str = Field(default="/", description="Cookie path")


class SessionSettings(BaseSettings):
    """Session management settings.

    Attributes:
        enabled: Enable session management.
        secret_key: Secret key for session signing.
        max_age: Session maximum age in seconds.
        cookie_name: Session cookie name.
        backend: Session storage backend.
    """

    model_config = SettingsConfigDict(
        env_prefix="SESSION_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable session management")
    secret_key: SecretStr | None = Field(
        default=None,
        description="Secret key for session signing",
    )
    max_age: int = Field(
        default=86400,  # 24 hours
        ge=1,
        description="Session maximum age in seconds",
    )
    cookie_name: str = Field(
        default="session_id",
        description="Session cookie name",
    )
    backend: str = Field(
        default="memory",
        description="Session storage backend (memory, redis, database)",
    )


class CryptoSettings(BaseSettings):
    """Cryptographic settings.

    Attributes:
        algorithm: Encryption algorithm.
        key_size: Key size in bits.
        secret_key: Secret key for encryption.
        salt_rounds: Salt rounds for password hashing.
    """

    model_config = SettingsConfigDict(
        env_prefix="CRYPTO_",
        extra="ignore",
        case_sensitive=False,
    )

    algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    key_size: int = Field(default=256, description="Key size in bits")
    secret_key: SecretStr | None = Field(
        default=None,
        description="Secret key for encryption",
    )
    salt_rounds: int = Field(
        default=12,
        ge=4,
        le=31,
        description="Salt rounds for password hashing",
    )


class TLSSettings(BaseSettings):
    """TLS/SSL settings.

    Attributes:
        enabled: Enable TLS.
        cert_file: Path to TLS certificate.
        key_file: Path to TLS private key.
        ca_file: Path to CA certificate.
        verify_client: Require client certificate verification.
        min_version: Minimum TLS version.
    """

    model_config = SettingsConfigDict(
        env_prefix="TLS_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable TLS")
    cert_file: str | None = Field(
        default=None,
        description="Path to TLS certificate",
    )
    key_file: str | None = Field(
        default=None,
        description="Path to TLS private key",
    )
    ca_file: str | None = Field(
        default=None,
        description="Path to CA certificate",
    )
    verify_client: bool = Field(
        default=False,
        description="Require client certificate verification",
    )
    min_version: str = Field(
        default="TLSv1.2",
        description="Minimum TLS version",
    )


class SecuritySettings(BaseSettings):
    """Comprehensive security configuration.

    Aggregates all security-related settings into a single
    configuration object.

    Attributes:
        cors: CORS settings.
        rate_limit: Rate limiting settings.
        headers: Security headers settings.
        cookie: Cookie settings.
        session: Session management settings.
        crypto: Cryptographic settings.
        tls: TLS/SSL settings.

    Example:
        >>> settings = SecuritySettings()
        >>> print(settings.cors.allow_origins)
        ['*']
    """

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Component settings
    cors: CORSSettings = Field(
        default_factory=CORSSettings,
        description="CORS settings",
    )
    rate_limit: RateLimitSettings = Field(
        default_factory=RateLimitSettings,
        description="Rate limiting settings",
    )
    headers: SecurityHeadersSettings = Field(
        default_factory=SecurityHeadersSettings,
        description="Security headers settings",
    )
    cookie: CookieSettings = Field(
        default_factory=CookieSettings,
        description="Cookie settings",
    )
    session: SessionSettings = Field(
        default_factory=SessionSettings,
        description="Session management settings",
    )
    crypto: CryptoSettings = Field(
        default_factory=CryptoSettings,
        description="Cryptographic settings",
    )
    tls: TLSSettings = Field(
        default_factory=TLSSettings,
        description="TLS/SSL settings",
    )

    @field_validator("cors", mode="before")
    @classmethod
    def validate_cors(cls, v: CORSSettings | dict | None) -> CORSSettings:
        """Handle CORS settings initialization."""
        if v is None:
            return CORSSettings()
        if isinstance(v, dict):
            return CORSSettings(**v)
        return v
