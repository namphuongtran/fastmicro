"""Tests for shared.config.base module.

This module tests the base configuration settings classes.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from shared.config.base import (
    BaseServiceSettings,
    SettingsError,
    clear_settings_cache,
    get_settings,
)


class TestBaseServiceSettings:
    """Tests for BaseServiceSettings class."""

    def test_default_values(self) -> None:
        """Should have sensible default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = BaseServiceSettings()

            assert settings.app_name == "microservice"
            assert settings.app_version == "0.1.0"
            assert settings.debug is False
            assert settings.environment == "development"

    def test_from_environment(self) -> None:
        """Should load values from environment variables."""
        env = {
            "APP_NAME": "test-service",
            "APP_VERSION": "1.2.3",
            "DEBUG": "true",
            "ENVIRONMENT": "production",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.app_name == "test-service"
            assert settings.app_version == "1.2.3"
            assert settings.debug is True
            assert settings.environment == "production"

    def test_server_settings(self) -> None:
        """Should have server configuration."""
        env = {
            "HOST": "127.0.0.1",
            "PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.host == "127.0.0.1"
            assert settings.port == 9000

    def test_default_server_settings(self) -> None:
        """Should have default server configuration."""
        with patch.dict(os.environ, {}, clear=True):
            settings = BaseServiceSettings()

            assert settings.host == "0.0.0.0"
            assert settings.port == 8000

    def test_is_development(self) -> None:
        """Should detect development environment."""
        env = {"ENVIRONMENT": "development"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False

    def test_is_production(self) -> None:
        """Should detect production environment."""
        env = {"ENVIRONMENT": "production"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.is_production is True
            assert settings.is_development is False
            assert settings.is_testing is False

    def test_is_testing(self) -> None:
        """Should detect testing environment."""
        env = {"ENVIRONMENT": "testing"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.is_testing is True
            assert settings.is_production is False
            assert settings.is_development is False

    def test_is_staging(self) -> None:
        """Should detect staging environment."""
        env = {"ENVIRONMENT": "staging"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.is_staging is True

    def test_log_level_default(self) -> None:
        """Should have default log level."""
        with patch.dict(os.environ, {}, clear=True):
            settings = BaseServiceSettings()

            assert settings.log_level == "INFO"

    def test_log_level_from_env(self) -> None:
        """Should load log level from environment."""
        env = {"LOG_LEVEL": "DEBUG"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.log_level == "DEBUG"

    def test_cors_settings(self) -> None:
        """Should have CORS configuration."""
        env = {"CORS_ORIGINS": '["http://localhost:3000", "https://example.com"]'}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert "http://localhost:3000" in settings.cors_origins
            assert "https://example.com" in settings.cors_origins

    def test_default_cors_allows_all(self) -> None:
        """Should default CORS to allow all origins."""
        with patch.dict(os.environ, {}, clear=True):
            settings = BaseServiceSettings()

            assert settings.cors_origins == ["*"]

    def test_allowed_hosts(self) -> None:
        """Should have allowed hosts configuration."""
        env = {"ALLOWED_HOSTS": '["example.com", "api.example.com"]'}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert "example.com" in settings.allowed_hosts

    def test_model_config_env_prefix(self) -> None:
        """Should not use env prefix by default."""
        env = {"APP_NAME": "test"}
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.app_name == "test"


class TestSettingsError:
    """Tests for SettingsError exception."""

    def test_settings_error(self) -> None:
        """Should create settings error."""
        error = SettingsError("Invalid configuration")

        assert str(error) == "Invalid configuration"
        assert isinstance(error, Exception)

    def test_settings_error_with_field(self) -> None:
        """Should include field information."""
        error = SettingsError("Invalid value", field="database_url")

        assert error.field == "database_url"
        assert "database_url" in str(error)


class TestGetSettings:
    """Tests for get_settings function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        clear_settings_cache()

    def test_returns_settings_instance(self) -> None:
        """Should return settings instance."""
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings(BaseServiceSettings)

            assert isinstance(settings, BaseServiceSettings)

    def test_caches_settings(self) -> None:
        """Should cache settings instance."""
        with patch.dict(os.environ, {}, clear=True):
            settings1 = get_settings(BaseServiceSettings)
            settings2 = get_settings(BaseServiceSettings)

            assert settings1 is settings2

    def test_clear_cache(self) -> None:
        """Should clear settings cache."""
        with patch.dict(os.environ, {"APP_NAME": "first"}, clear=True):
            settings1 = get_settings(BaseServiceSettings)

        clear_settings_cache()

        with patch.dict(os.environ, {"APP_NAME": "second"}, clear=True):
            settings2 = get_settings(BaseServiceSettings)

        assert settings1.app_name == "first"
        assert settings2.app_name == "second"
        assert settings1 is not settings2
