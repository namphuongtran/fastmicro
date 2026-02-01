"""Tests for shared.config.database module.

This module tests database configuration settings.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from shared.config.database import DatabaseSettings, DatabaseType


class TestDatabaseType:
    """Tests for DatabaseType enum."""

    def test_postgresql(self) -> None:
        """Should have PostgreSQL type."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"

    def test_mysql(self) -> None:
        """Should have MySQL type."""
        assert DatabaseType.MYSQL.value == "mysql"

    def test_sqlite(self) -> None:
        """Should have SQLite type."""
        assert DatabaseType.SQLITE.value == "sqlite"

    def test_mssql(self) -> None:
        """Should have MSSQL type."""
        assert DatabaseType.MSSQL.value == "mssql"


class TestDatabaseSettings:
    """Tests for DatabaseSettings class."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.host == "localhost"
            assert settings.port == 5432
            assert settings.db_type == DatabaseType.POSTGRESQL

    def test_from_environment(self) -> None:
        """Should load from environment variables with DB_ prefix."""
        env = {
            "DB_HOST": "db.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "mydb",
            "DB_USER": "myuser",
            "DB_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.host == "db.example.com"
            assert settings.port == 5433
            assert settings.name == "mydb"
            assert settings.user == "myuser"
            assert settings.password.get_secret_value() == "secret123"

    def test_pool_settings(self) -> None:
        """Should have connection pool settings."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_POOL_SIZE": "10",
            "DB_MAX_OVERFLOW": "20",
            "DB_POOL_TIMEOUT": "60",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.pool_size == 10
            assert settings.max_overflow == 20
            assert settings.pool_timeout == 60

    def test_default_pool_settings(self) -> None:
        """Should have default pool settings."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.pool_size == 5
            assert settings.max_overflow == 10
            assert settings.pool_timeout == 30

    def test_postgresql_sync_url(self) -> None:
        """Should generate sync PostgreSQL URL."""
        env = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_TYPE": "postgresql",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.sync_url == "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_postgresql_async_url(self) -> None:
        """Should generate async PostgreSQL URL."""
        env = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_TYPE": "postgresql",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert (
                settings.async_url == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
            )

    def test_mysql_sync_url(self) -> None:
        """Should generate sync MySQL URL."""
        env = {
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_TYPE": "mysql",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.sync_url == "mysql+pymysql://testuser:testpass@localhost:3306/testdb"

    def test_mysql_async_url(self) -> None:
        """Should generate async MySQL URL."""
        env = {
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_TYPE": "mysql",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.async_url == "mysql+aiomysql://testuser:testpass@localhost:3306/testdb"

    def test_sqlite_url(self) -> None:
        """Should generate SQLite URL."""
        env = {
            "DB_NAME": "./data/test.db",
            "DB_TYPE": "sqlite",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.sync_url == "sqlite:///./data/test.db"
            assert settings.async_url == "sqlite+aiosqlite:///./data/test.db"

    def test_mssql_url(self) -> None:
        """Should generate MSSQL URL."""
        env = {
            "DB_HOST": "localhost",
            "DB_PORT": "1433",
            "DB_NAME": "testdb",
            "DB_USER": "sa",
            "DB_PASSWORD": "testpass",
            "DB_TYPE": "mssql",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert "mssql+pyodbc://sa:testpass@localhost:1433/testdb" in settings.sync_url

    def test_echo_setting(self) -> None:
        """Should have SQL echo setting for debugging."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_ECHO": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.echo is True

    def test_echo_default_false(self) -> None:
        """Should default echo to false."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.echo is False

    def test_pool_pre_ping(self) -> None:
        """Should have pool pre-ping setting."""
        env = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_POOL_PRE_PING": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()

            assert settings.pool_pre_ping is True

    def test_default_port_by_type(self) -> None:
        """Should use default port based on database type."""
        # PostgreSQL default
        env = {"DB_NAME": "test", "DB_USER": "user", "DB_PASSWORD": "pass", "DB_TYPE": "postgresql"}
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()
            assert settings.port == 5432

        # MySQL default
        env = {"DB_NAME": "test", "DB_USER": "user", "DB_PASSWORD": "pass", "DB_TYPE": "mysql"}
        with patch.dict(os.environ, env, clear=True):
            settings = DatabaseSettings()
            assert settings.port == 3306
