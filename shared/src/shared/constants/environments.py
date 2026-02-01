"""
Environment constants and detection utilities.

This module provides an enum for application environments with utilities
for environment detection, validation, and environment-specific configuration.

Example:
    >>> from shared.constants import Environment
    >>> env = Environment.current()
    >>> if env.is_production:
    ...     print("Running in production!")
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Self

__all__ = ["ENVIRONMENT_ALIASES", "Environment"]


# Module-level aliases mapping - kept outside the enum for Python 3.14 compatibility
ENVIRONMENT_ALIASES: dict[str, str] = {
    "dev": "development",
    "develop": "development",
    "prod": "production",
    "prd": "production",
    "stg": "staging",
    "stage": "staging",
    "test": "testing",
    "tests": "testing",
    "loc": "local",
}


class Environment(Enum):
    """
    Application environment enumeration.

    Provides environment values with utilities for detection and
    environment-specific configuration.

    Example:
        >>> Environment.PRODUCTION.is_production
        True
        >>> Environment.current()
        <Environment.DEVELOPMENT: 'development'>
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    LOCAL = "local"

    @classmethod
    def from_string(
        cls,
        value: str,
        *,
        default: Self | None = None,
    ) -> Self:
        """
        Create Environment from a string value.

        Handles case-insensitive matching and common aliases.

        Args:
            value: The environment string (e.g., "production", "prod", "PROD").
            default: Default value to return if not found (raises ValueError if None).

        Returns:
            The matching Environment enum member.

        Raises:
            ValueError: If value is not recognized and no default provided.

        Example:
            >>> Environment.from_string("prod")
            <Environment.PRODUCTION: 'production'>
        """
        normalized = value.lower().strip()

        # Check for alias using module-level constant
        if normalized in ENVIRONMENT_ALIASES:
            normalized = ENVIRONMENT_ALIASES[normalized]

        # Try to match enum value
        for env in cls:
            if env.value == normalized:
                return env

        if default is not None:
            return default

        valid_values = [e.value for e in cls]
        raise ValueError(f"Unknown environment: '{value}'. Valid values: {valid_values}")

    @classmethod
    def current(cls) -> Self:
        """
        Detect and return the current environment.

        Checks environment variables in order:
        1. ENVIRONMENT
        2. APP_ENV
        3. Defaults to DEVELOPMENT

        Returns:
            The detected Environment.

        Example:
            >>> # With ENVIRONMENT=production set
            >>> Environment.current()
            <Environment.PRODUCTION: 'production'>
        """
        # Check common environment variable names
        env_value = os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV")

        if env_value:
            return cls.from_string(env_value, default=cls.DEVELOPMENT)

        return cls.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """
        Check if this is the production environment.

        Returns:
            True if production environment.
        """
        return self == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """
        Check if this is a development environment.

        Includes both DEVELOPMENT and LOCAL environments.

        Returns:
            True if development or local environment.
        """
        return self in (Environment.DEVELOPMENT, Environment.LOCAL)

    @property
    def is_testing(self) -> bool:
        """
        Check if this is the testing environment.

        Returns:
            True if testing environment.
        """
        return self == Environment.TESTING

    @property
    def allows_debug(self) -> bool:
        """
        Check if debug mode is allowed in this environment.

        Debug is allowed in development, local, and testing environments.

        Returns:
            True if debug mode is allowed.
        """
        return self in (
            Environment.DEVELOPMENT,
            Environment.LOCAL,
            Environment.TESTING,
        )

    @property
    def requires_https(self) -> bool:
        """
        Check if HTTPS is required in this environment.

        HTTPS is required in production and staging environments.

        Returns:
            True if HTTPS is required.
        """
        return self in (Environment.PRODUCTION, Environment.STAGING)

    def get_log_level(self) -> str:
        """
        Get the recommended log level for this environment.

        Returns:
            Log level string (e.g., "DEBUG", "INFO", "WARNING").
        """
        log_levels = {
            Environment.DEVELOPMENT: "DEBUG",
            Environment.LOCAL: "DEBUG",
            Environment.TESTING: "WARNING",
            Environment.STAGING: "INFO",
            Environment.PRODUCTION: "INFO",
        }
        return log_levels.get(self, "INFO")

    def get_log_format(self) -> str:
        """
        Get the recommended log format for this environment.

        Returns:
            Log format string ("json" for production, "console" for development).
        """
        if self in (Environment.PRODUCTION, Environment.STAGING):
            return "json"
        return "console"
