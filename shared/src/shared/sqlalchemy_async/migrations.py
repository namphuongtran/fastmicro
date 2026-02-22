"""Alembic migration utilities for async SQLAlchemy services.

Provides helpers for integrating Alembic database migrations into
async microservices:

* **AlembicConfig** - dataclass holding migration paths and DB URL.
* **create_alembic_config** - builds an ``alembic.config.Config`` from the
  dataclass (avoids manual ``alembic.ini`` file management).
* **run_migrations_online** - async helper to run migrations inside an
  ``AsyncEngine`` connection (suitable for ``env.py``).
* **stamp_head / current_revision** - programmatic helpers for CI/CD scripts.
* **generate_migration_env** - generates a ready-to-use ``env.py`` template.

Usage from application startup::

    from shared.sqlalchemy_async.migrations import (
        AlembicMigrationConfig,
        run_upgrade_to_head,
    )

    config = AlembicMigrationConfig(
        database_url="postgresql+asyncpg://localhost/mydb",
        script_location="./migrations",
    )
    await run_upgrade_to_head(config)

.. note::
   Requires the ``alembic`` package: ``pip install alembic``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlembicMigrationConfig:
    """Configuration for Alembic migrations.

    Attributes:
        database_url: Async database URL (e.g. ``postgresql+asyncpg://…``).
            For Alembic the async URL is automatically converted to a sync URL.
        script_location: Path to the Alembic versions directory.
        version_table: Name of the Alembic version tracking table.
        target_metadata: SQLAlchemy ``MetaData`` for autogenerate support.
        file_template: Alembic revision filename template.
        extra_context: Additional context passed to ``env.py``.
    """

    database_url: str
    script_location: str = "./migrations"
    version_table: str = "alembic_version"
    target_metadata: Any = None
    file_template: str = "%%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s"
    extra_context: dict[str, Any] = field(default_factory=dict)


def _async_url_to_sync(url: str) -> str:
    """Convert an async database URL to its sync equivalent.

    Examples:
        postgresql+asyncpg://… → postgresql://…
        sqlite+aiosqlite://… → sqlite://…
    """
    replacements = {
        "postgresql+asyncpg": "postgresql",
        "sqlite+aiosqlite": "sqlite",
        "mysql+aiomysql": "mysql+pymysql",
    }
    for async_driver, sync_driver in replacements.items():
        if url.startswith(async_driver):
            return url.replace(async_driver, sync_driver, 1)
    return url


def create_alembic_config(
    migration_config: AlembicMigrationConfig,
) -> Any:
    """Build an ``alembic.config.Config`` object programmatically.

    This removes the need for a static ``alembic.ini`` file.

    Args:
        migration_config: Application migration configuration.

    Returns:
        ``alembic.config.Config`` ready for command-line operations.

    Raises:
        ImportError: If ``alembic`` is not installed.
    """
    try:
        from alembic.config import Config as _AlembicConfig
    except ImportError as exc:
        raise ImportError(
            "alembic is required for migration utilities. "
            "Install it with: pip install alembic"
        ) from exc

    alembic_cfg = _AlembicConfig()
    alembic_cfg.set_main_option("script_location", migration_config.script_location)
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        _async_url_to_sync(migration_config.database_url),
    )
    alembic_cfg.set_main_option("version_table", migration_config.version_table)
    alembic_cfg.set_main_option("file_template", migration_config.file_template)

    return alembic_cfg


async def run_upgrade_to_head(
    config: AlembicMigrationConfig,
) -> None:
    """Apply all pending migrations up to ``head``.

    Suitable for application startup or CI/CD scripts.

    Args:
        config: Migration configuration.

    Raises:
        ImportError: If ``alembic`` is not installed.
    """
    try:
        from alembic import command as alembic_command
    except ImportError as exc:
        raise ImportError(
            "alembic is required for migration utilities. "
            "Install it with: pip install alembic"
        ) from exc

    alembic_cfg = create_alembic_config(config)
    logger.info("Running Alembic upgrade to head (script_location=%s)", config.script_location)
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("Alembic upgrade complete")


async def run_downgrade(
    config: AlembicMigrationConfig,
    revision: str = "-1",
) -> None:
    """Downgrade by one revision (or to a specific revision).

    Args:
        config: Migration configuration.
        revision: Target revision (default ``"-1"`` = one step back).
    """
    try:
        from alembic import command as alembic_command
    except ImportError as exc:
        raise ImportError(
            "alembic is required for migration utilities. "
            "Install it with: pip install alembic"
        ) from exc

    alembic_cfg = create_alembic_config(config)
    logger.info("Running Alembic downgrade to %s", revision)
    alembic_command.downgrade(alembic_cfg, revision)


def stamp_head(config: AlembicMigrationConfig) -> None:
    """Mark the database as being at ``head`` without running migrations.

    Useful for fresh databases where the schema was created by
    ``create_all()``.

    Args:
        config: Migration configuration.
    """
    try:
        from alembic import command as alembic_command
    except ImportError as exc:
        raise ImportError(
            "alembic is required for migration utilities. "
            "Install it with: pip install alembic"
        ) from exc

    alembic_cfg = create_alembic_config(config)
    alembic_command.stamp(alembic_cfg, "head")
    logger.info("Alembic stamped head")


def get_current_revision(config: AlembicMigrationConfig) -> str | None:
    """Get the current migration revision from the database.

    Args:
        config: Migration configuration.

    Returns:
        Current revision string, or ``None`` if no migrations have been applied.
    """
    try:
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise ImportError(
            "alembic is required for migration utilities. "
            "Install it with: pip install alembic"
        ) from exc

    sync_url = _async_url_to_sync(config.database_url)
    engine = create_engine(sync_url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Template generation
# ---------------------------------------------------------------------------

_ENV_PY_TEMPLATE = '''\
"""Alembic env.py - auto-generated by shared.sqlalchemy_async.migrations."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import your models' MetaData here:
# from myapp.models import Base
# target_metadata = Base.metadata
target_metadata = None

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''


def generate_migration_scaffold(
    base_dir: str | Path,
) -> Path:
    """Generate an Alembic-compatible migration scaffold directory.

    Creates ``<base_dir>/versions/`` and a minimal ``env.py``.

    Args:
        base_dir: Root directory for the Alembic script location.

    Returns:
        Path to the generated ``env.py``.
    """
    base = Path(base_dir)
    versions_dir = base / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    env_py = base / "env.py"
    if not env_py.exists():
        env_py.write_text(_ENV_PY_TEMPLATE, encoding="utf-8")
        logger.info("Generated Alembic env.py at %s", env_py)

    # Create script.py.mako template
    mako = base / "script.py.mako"
    if not mako.exists():
        mako.write_text(
            _MAKO_TEMPLATE,
            encoding="utf-8",
        )
        logger.info("Generated script.py.mako at %s", mako)

    return env_py


_MAKO_TEMPLATE = '''\
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''


__all__ = [
    "AlembicMigrationConfig",
    "create_alembic_config",
    "generate_migration_scaffold",
    "get_current_revision",
    "run_downgrade",
    "run_upgrade_to_head",
    "stamp_head",
]
