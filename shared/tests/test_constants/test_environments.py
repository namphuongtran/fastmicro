"""
Unit tests for environment constants.

Tests cover:
- Environment enum values
- Environment detection
- Environment-specific configuration helpers
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from shared.constants.environments import Environment


class TestEnvironmentValues:
    """Tests for Environment enum values."""

    def test_development_value(self) -> None:
        assert Environment.DEVELOPMENT.value == "development"

    def test_staging_value(self) -> None:
        assert Environment.STAGING.value == "staging"

    def test_production_value(self) -> None:
        assert Environment.PRODUCTION.value == "production"

    def test_testing_value(self) -> None:
        assert Environment.TESTING.value == "testing"

    def test_local_value(self) -> None:
        assert Environment.LOCAL.value == "local"


class TestEnvironmentFromString:
    """Tests for creating Environment from string."""

    def test_from_string_lowercase(self) -> None:
        """Environment can be created from lowercase string."""
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("production") == Environment.PRODUCTION

    def test_from_string_uppercase(self) -> None:
        """Environment can be created from uppercase string."""
        assert Environment.from_string("DEVELOPMENT") == Environment.DEVELOPMENT
        assert Environment.from_string("PRODUCTION") == Environment.PRODUCTION

    def test_from_string_mixed_case(self) -> None:
        """Environment can be created from mixed case string."""
        assert Environment.from_string("Production") == Environment.PRODUCTION
        assert Environment.from_string("DeVeLoPmEnT") == Environment.DEVELOPMENT

    def test_from_string_with_aliases(self) -> None:
        """Environment supports common aliases."""
        assert Environment.from_string("dev") == Environment.DEVELOPMENT
        assert Environment.from_string("prod") == Environment.PRODUCTION
        assert Environment.from_string("stg") == Environment.STAGING
        assert Environment.from_string("test") == Environment.TESTING

    def test_from_string_invalid(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown environment"):
            Environment.from_string("invalid")

    def test_from_string_with_default(self) -> None:
        """from_string can return default for invalid values."""
        result = Environment.from_string("invalid", default=Environment.DEVELOPMENT)
        assert result == Environment.DEVELOPMENT


class TestEnvironmentDetection:
    """Tests for automatic environment detection."""

    def test_current_from_env_var(self) -> None:
        """current() reads from ENVIRONMENT env var."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert Environment.current() == Environment.PRODUCTION

    def test_current_from_app_env_var(self) -> None:
        """current() falls back to APP_ENV env var."""
        with patch.dict(os.environ, {"APP_ENV": "staging"}, clear=False):
            # Remove ENVIRONMENT if it exists
            env = os.environ.copy()
            env.pop("ENVIRONMENT", None)
            env["APP_ENV"] = "staging"
            with patch.dict(os.environ, env, clear=True):
                assert Environment.current() == Environment.STAGING

    def test_current_default(self) -> None:
        """current() defaults to DEVELOPMENT when no env var."""
        with patch.dict(os.environ, {}, clear=True):
            assert Environment.current() == Environment.DEVELOPMENT


class TestEnvironmentHelpers:
    """Tests for environment helper methods."""

    def test_is_production(self) -> None:
        """is_production checks for production environment."""
        assert Environment.PRODUCTION.is_production is True
        assert Environment.DEVELOPMENT.is_production is False
        assert Environment.STAGING.is_production is False

    def test_is_development(self) -> None:
        """is_development checks for development environments."""
        assert Environment.DEVELOPMENT.is_development is True
        assert Environment.LOCAL.is_development is True
        assert Environment.PRODUCTION.is_development is False

    def test_is_testing(self) -> None:
        """is_testing checks for testing environment."""
        assert Environment.TESTING.is_testing is True
        assert Environment.DEVELOPMENT.is_testing is False

    def test_allows_debug(self) -> None:
        """allows_debug is True for non-production environments."""
        assert Environment.DEVELOPMENT.allows_debug is True
        assert Environment.LOCAL.allows_debug is True
        assert Environment.TESTING.allows_debug is True
        assert Environment.PRODUCTION.allows_debug is False
        assert Environment.STAGING.allows_debug is False

    def test_requires_https(self) -> None:
        """requires_https is True for production-like environments."""
        assert Environment.PRODUCTION.requires_https is True
        assert Environment.STAGING.requires_https is True
        assert Environment.DEVELOPMENT.requires_https is False
        assert Environment.LOCAL.requires_https is False


class TestEnvironmentConfigHelpers:
    """Tests for environment-based configuration helpers."""

    def test_get_log_level(self) -> None:
        """get_log_level returns appropriate level for environment."""
        assert Environment.PRODUCTION.get_log_level() == "INFO"
        assert Environment.DEVELOPMENT.get_log_level() == "DEBUG"
        assert Environment.LOCAL.get_log_level() == "DEBUG"
        assert Environment.TESTING.get_log_level() == "WARNING"

    def test_get_log_format(self) -> None:
        """get_log_format returns appropriate format."""
        assert Environment.PRODUCTION.get_log_format() == "json"
        assert Environment.DEVELOPMENT.get_log_format() == "console"
        assert Environment.LOCAL.get_log_format() == "console"
