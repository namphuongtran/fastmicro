"""Identity Service configuration settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Identity Service settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="identity-service", description="Application name")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="Environment"
    )
    app_debug: bool = Field(default=False, description="Debug mode")
    app_port: int = Field(default=8003, ge=1, le=65535, description="Application port")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )

    # Database
    database_url: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://postgres:postgres@localhost:5432/identity"),
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    database_pool_overflow: int = Field(default=20, ge=0, le=100, description="Pool overflow")

    # Redis (Sessions, Auth Codes, Token Blacklist)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_pool_size: int = Field(default=10, ge=1, le=100, description="Redis pool size")

    # JWT / Token Configuration
    jwt_issuer: str = Field(
        default="http://localhost:8003",
        description="JWT issuer URL (should match your IdP URL)",
    )
    jwt_audience: str = Field(
        default="http://localhost:8003",
        description="Default JWT audience",
    )
    jwt_algorithm: Literal["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"] = Field(
        default="RS256", description="JWT signing algorithm"
    )
    jwt_private_key_path: str = Field(
        default="/app/keys/private.pem",
        description="Path to RSA private key for signing",
    )
    jwt_public_key_path: str = Field(
        default="/app/keys/public.pem",
        description="Path to RSA public key for verification",
    )

    # Token Lifetimes (in seconds)
    access_token_lifetime: int = Field(
        default=3600, ge=60, le=86400, description="Access token lifetime"
    )
    refresh_token_lifetime: int = Field(
        default=2592000, ge=3600, le=31536000, description="Refresh token lifetime (30 days)"
    )
    authorization_code_lifetime: int = Field(
        default=600, ge=60, le=3600, description="Authorization code lifetime"
    )
    id_token_lifetime: int = Field(default=3600, ge=60, le=86400, description="ID token lifetime")

    # Session Configuration
    session_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production-use-secrets-manager"),
        description="Session encryption key",
    )
    session_cookie_name: str = Field(default="identity_session", description="Session cookie name")
    session_max_age: int = Field(
        default=86400, ge=3600, le=604800, description="Session max age (1 day)"
    )

    # Security
    password_min_length: int = Field(
        default=12, ge=8, le=128, description="Minimum password length"
    )
    password_require_uppercase: bool = Field(default=True, description="Require uppercase")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase")
    password_require_digit: bool = Field(default=True, description="Require digit")
    password_require_special: bool = Field(default=True, description="Require special character")
    bcrypt_rounds: int = Field(default=12, ge=4, le=15, description="bcrypt work factor")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, ge=1, description="Requests per window")
    rate_limit_window: int = Field(default=60, ge=1, description="Window in seconds")
    login_max_attempts: int = Field(default=5, ge=1, le=20, description="Max login attempts")
    login_lockout_duration: int = Field(
        default=900, ge=60, le=86400, description="Lockout duration (15 min)"
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")

    # OpenTelemetry
    otel_enabled: bool = Field(default=True, description="Enable OpenTelemetry")
    otel_service_name: str = Field(default="identity-service", description="Service name")
    otel_exporter_endpoint: str = Field(
        default="http://localhost:4317", description="OTLP exporter endpoint"
    )

    # Admin Configuration
    admin_email: str = Field(default="admin@example.com", description="Default admin email")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
