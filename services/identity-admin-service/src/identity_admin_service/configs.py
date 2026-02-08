"""Configuration settings for Identity Admin Service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="identity-admin-service")
    app_env: str = Field(default="development")
    app_port: int = Field(default=8081)
    log_level: str = Field(default="INFO")

    # Database - Shared with identity-service
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/identity_db"
    )
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)
    database_echo: bool = Field(default=False)

    # Identity Service (for token validation)
    identity_service_url: str = Field(default="http://localhost:8000")

    # Admin Session
    admin_session_secret: str = Field(default="change-me-in-production-admin-secret")
    admin_session_expire_hours: int = Field(default=8)
    admin_require_mfa: bool = Field(default=False)

    # Security
    allowed_admin_ips: str = Field(default="*")  # Comma-separated IPs or *
    cors_origins: list[str] = Field(default=["http://localhost:8081"])
    cors_allow_credentials: bool = Field(default=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() in ("production", "prod")

    @property
    def allowed_ip_list(self) -> list[str]:
        """Parse allowed admin IPs into a list."""
        if self.allowed_admin_ips == "*":
            return ["*"]
        return [ip.strip() for ip in self.allowed_admin_ips.split(",") if ip.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
