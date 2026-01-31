"""Database configuration settings.

This module provides database-specific settings with support
for multiple database backends (PostgreSQL, MySQL, SQLite, MSSQL).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MSSQL = "mssql"


# Default ports for each database type
DEFAULT_PORTS: dict[DatabaseType, int] = {
    DatabaseType.POSTGRESQL: 5432,
    DatabaseType.MYSQL: 3306,
    DatabaseType.SQLITE: 0,
    DatabaseType.MSSQL: 1433,
}

# Sync drivers for each database type
SYNC_DRIVERS: dict[DatabaseType, str] = {
    DatabaseType.POSTGRESQL: "postgresql",
    DatabaseType.MYSQL: "mysql+pymysql",
    DatabaseType.SQLITE: "sqlite",
    DatabaseType.MSSQL: "mssql+pyodbc",
}

# Async drivers for each database type
ASYNC_DRIVERS: dict[DatabaseType, str] = {
    DatabaseType.POSTGRESQL: "postgresql+asyncpg",
    DatabaseType.MYSQL: "mysql+aiomysql",
    DatabaseType.SQLITE: "sqlite+aiosqlite",
    DatabaseType.MSSQL: "mssql+aioodbc",
}


class DatabaseSettings(BaseSettings):
    """Database connection settings.

    Supports PostgreSQL, MySQL, SQLite, and MSSQL with both
    sync and async connection URL generation.

    Attributes:
        db_type: Database type (postgresql, mysql, sqlite, mssql).
        host: Database host address.
        port: Database port number.
        name: Database name.
        user: Database username.
        password: Database password.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        pool_timeout: Pool connection timeout in seconds.
        pool_pre_ping: Enable connection health checks.
        echo: Enable SQL query logging.

    Example:
        >>> settings = DatabaseSettings()
        >>> print(settings.async_url)
        postgresql+asyncpg://user:pass@localhost:5432/mydb
    """

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Connection settings
    db_type: DatabaseType = Field(
        default=DatabaseType.POSTGRESQL,
        validation_alias="DB_TYPE",
        description="Database type",
    )
    host: str = Field(default="localhost", description="Database host")
    port: int | None = Field(default=None, ge=0, le=65535, description="Database port")
    name: str = Field(..., description="Database name")
    user: str | None = Field(default=None, description="Database username")
    password: SecretStr | None = Field(default=None, description="Database password")

    # Connection pool settings
    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    pool_pre_ping: bool = Field(
        default=True,
        description="Enable connection health check before use",
    )

    # Debugging
    echo: bool = Field(default=False, description="Enable SQL query logging")

    @model_validator(mode="after")
    def set_default_port(self) -> "DatabaseSettings":
        """Set default port based on database type if not explicitly set."""
        if self.port is None:
            object.__setattr__(self, "port", DEFAULT_PORTS.get(self.db_type, 5432))
        return self

    @property
    def sync_url(self) -> str:
        """Generate synchronous database URL.

        Returns:
            Database connection URL for sync operations.
        """
        return self._build_url(async_driver=False)

    @property
    def async_url(self) -> str:
        """Generate asynchronous database URL.

        Returns:
            Database connection URL for async operations.
        """
        return self._build_url(async_driver=True)

    def _build_url(self, async_driver: bool = False) -> str:
        """Build database connection URL.

        Args:
            async_driver: Use async driver if True.

        Returns:
            Formatted database connection URL.
        """
        drivers = ASYNC_DRIVERS if async_driver else SYNC_DRIVERS
        driver = drivers[self.db_type]

        # SQLite special case
        if self.db_type == DatabaseType.SQLITE:
            return f"{driver}:///{self.name}"

        # Build credentials part
        credentials = ""
        if self.user:
            password = self.password.get_secret_value() if self.password else ""
            credentials = f"{self.user}:{password}@"

        # MSSQL special case with ODBC driver
        if self.db_type == DatabaseType.MSSQL:
            base_url = f"{driver}://{credentials}{self.host}:{self.port}/{self.name}"
            return f"{base_url}?driver=ODBC+Driver+18+for+SQL+Server"

        return f"{driver}://{credentials}{self.host}:{self.port}/{self.name}"
