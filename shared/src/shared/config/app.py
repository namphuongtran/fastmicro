"""Application configuration settings.

This module provides application-level settings including
pagination, API versioning, and general app behavior options.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaginationSettings(BaseSettings):
    """Pagination configuration settings.

    Attributes:
        default_page_size: Default number of items per page.
        max_page_size: Maximum allowed page size.
        page_param: Query parameter name for page number.
        size_param: Query parameter name for page size.
    """

    model_config = SettingsConfigDict(
        env_prefix="PAGINATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    default_page_size: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Default number of items per page",
    )
    max_page_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum allowed page size",
    )
    page_param: str = Field(
        default="page",
        description="Query parameter name for page number",
    )
    size_param: str = Field(
        default="size",
        description="Query parameter name for page size",
    )


class AppSettings(BaseSettings):
    """Application-level settings.

    Provides configuration for general application behavior
    including API versioning, documentation, and maintenance mode.

    Attributes:
        title: Application title for documentation.
        description: Application description.
        api_prefix: Prefix for API routes.
        api_version: Current API version.
        docs_enabled: Enable API documentation endpoints.
        maintenance_mode: Enable maintenance mode.
        max_request_size: Maximum request body size in bytes.
        request_timeout: Default request timeout in seconds.
        pagination: Pagination configuration.

    Example:
        >>> settings = AppSettings()
        >>> print(settings.api_prefix)
        /api/v1
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application metadata
    title: str = Field(
        default="Microservice API",
        description="Application title",
    )
    description: str = Field(
        default="",
        description="Application description",
    )

    # API settings
    api_prefix: str = Field(
        default="/api/v1",
        description="Prefix for API routes",
    )
    api_version: str = Field(
        default="1.0.0",
        description="Current API version",
    )

    # Documentation
    docs_enabled: bool = Field(
        default=True,
        description="Enable API documentation endpoints",
    )

    # Operational settings
    maintenance_mode: bool = Field(
        default=False,
        description="Enable maintenance mode",
    )
    max_request_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1,
        description="Maximum request body size in bytes",
    )
    request_timeout: int = Field(
        default=30,
        ge=1,
        description="Default request timeout in seconds",
    )

    # Nested settings
    pagination: PaginationSettings = Field(
        default_factory=PaginationSettings,
        description="Pagination configuration",
    )

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, v: str) -> str:
        """Ensure API prefix starts with /."""
        if not v.startswith("/"):
            v = f"/{v}"
        return v.rstrip("/")
