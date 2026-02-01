"""Tests for shared.config.auth module.

This module tests authentication configuration settings.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from shared.config.auth import AuthSettings


class TestAuthSettings:
    """Tests for AuthSettings class."""

    def test_required_secret_key(self) -> None:
        """Should require secret key."""
        env = {"AUTH_SECRET_KEY": "super-secret-key-for-testing"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.secret_key.get_secret_value() == "super-secret-key-for-testing"

    def test_algorithm_default(self) -> None:
        """Should default to HS256 algorithm."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.algorithm == "HS256"

    def test_algorithm_from_env(self) -> None:
        """Should load algorithm from environment."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_ALGORITHM": "RS256",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.algorithm == "RS256"

    def test_access_token_expire(self) -> None:
        """Should have access token expiration setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.access_token_expire_minutes == 60

    def test_access_token_expire_default(self) -> None:
        """Should default access token expiration to 30 minutes."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.access_token_expire_minutes == 30

    def test_refresh_token_expire(self) -> None:
        """Should have refresh token expiration setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_REFRESH_TOKEN_EXPIRE_DAYS": "14",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.refresh_token_expire_days == 14

    def test_refresh_token_expire_default(self) -> None:
        """Should default refresh token expiration to 7 days."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.refresh_token_expire_days == 7

    def test_token_url(self) -> None:
        """Should have token URL setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_TOKEN_URL": "/api/v1/auth/token",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.token_url == "/api/v1/auth/token"

    def test_token_url_default(self) -> None:
        """Should default token URL to /token."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.token_url == "/token"

    def test_scopes(self) -> None:
        """Should support OAuth2 scopes configuration."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_SCOPES": '{"read": "Read access", "write": "Write access"}',
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.scopes == {"read": "Read access", "write": "Write access"}

    def test_scopes_default(self) -> None:
        """Should have default scopes."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert "read" in settings.scopes
            assert "write" in settings.scopes

    def test_issuer(self) -> None:
        """Should have JWT issuer setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_ISSUER": "https://auth.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.issuer == "https://auth.example.com"

    def test_audience(self) -> None:
        """Should have JWT audience setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_AUDIENCE": "https://api.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.audience == "https://api.example.com"

    def test_password_min_length(self) -> None:
        """Should have password minimum length setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_PASSWORD_MIN_LENGTH": "12",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.password_min_length == 12

    def test_password_min_length_default(self) -> None:
        """Should default password minimum length to 8."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.password_min_length == 8

    def test_api_key_header(self) -> None:
        """Should have API key header name setting."""
        env = {
            "AUTH_SECRET_KEY": "test-key",
            "AUTH_API_KEY_HEADER": "X-Custom-Api-Key",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.api_key_header == "X-Custom-Api-Key"

    def test_api_key_header_default(self) -> None:
        """Should default API key header to X-API-Key."""
        env = {"AUTH_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            settings = AuthSettings()

            assert settings.api_key_header == "X-API-Key"
