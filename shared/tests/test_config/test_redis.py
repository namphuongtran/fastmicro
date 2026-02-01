"""Tests for shared.config.redis module.

This module tests Redis configuration settings.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from shared.config.redis import RedisSettings


class TestRedisSettings:
    """Tests for RedisSettings class."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.host == "localhost"
            assert settings.port == 6379
            assert settings.db == 0
            assert settings.password is None

    def test_from_environment(self) -> None:
        """Should load from environment variables with REDIS_ prefix."""
        env = {
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_DB": "1",
            "REDIS_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.host == "redis.example.com"
            assert settings.port == 6380
            assert settings.db == 1
            assert settings.password.get_secret_value() == "secret"

    def test_url_without_password(self) -> None:
        """Should generate URL without password."""
        env = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.url == "redis://localhost:6379/0"

    def test_url_with_password(self) -> None:
        """Should generate URL with password."""
        env = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
            "REDIS_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.url == "redis://:secret123@localhost:6379/0"

    def test_url_with_username(self) -> None:
        """Should generate URL with username and password."""
        env = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
            "REDIS_USERNAME": "myuser",
            "REDIS_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.url == "redis://myuser:secret123@localhost:6379/0"

    def test_ssl_enabled(self) -> None:
        """Should support SSL connection."""
        env = {
            "REDIS_HOST": "redis.example.com",
            "REDIS_SSL": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.ssl is True
            assert settings.url.startswith("rediss://")

    def test_ssl_disabled_default(self) -> None:
        """Should default SSL to disabled."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.ssl is False
            assert settings.url.startswith("redis://")

    def test_connection_pool_settings(self) -> None:
        """Should have connection pool settings."""
        env = {
            "REDIS_MAX_CONNECTIONS": "20",
            "REDIS_SOCKET_TIMEOUT": "10.0",
            "REDIS_SOCKET_CONNECT_TIMEOUT": "5.0",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.max_connections == 20
            assert settings.socket_timeout == 10.0
            assert settings.socket_connect_timeout == 5.0

    def test_default_pool_settings(self) -> None:
        """Should have default pool settings."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.max_connections == 10
            assert settings.socket_timeout == 5.0
            assert settings.socket_connect_timeout == 5.0

    def test_key_prefix(self) -> None:
        """Should support key prefix for namespacing."""
        env = {"REDIS_KEY_PREFIX": "myapp:"}
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.key_prefix == "myapp:"

    def test_default_key_prefix_empty(self) -> None:
        """Should default key prefix to empty."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.key_prefix == ""

    def test_ttl_default(self) -> None:
        """Should have default TTL setting."""
        env = {"REDIS_DEFAULT_TTL": "3600"}
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.default_ttl == 3600

    def test_cluster_mode(self) -> None:
        """Should support cluster mode flag."""
        env = {"REDIS_CLUSTER_MODE": "true"}
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

            assert settings.cluster_mode is True

    def test_cluster_mode_default_false(self) -> None:
        """Should default cluster mode to false."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.cluster_mode is False
