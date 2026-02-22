"""Tests for Alembic migration utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.sqlalchemy_async.migrations import (
    AlembicMigrationConfig,
    _async_url_to_sync,
    create_alembic_config,
    generate_migration_scaffold,
    run_downgrade,
    run_upgrade_to_head,
    stamp_head,
)

# ---------------------------------------------------------------------------
# AlembicMigrationConfig
# ---------------------------------------------------------------------------


class TestAlembicMigrationConfig:
    def test_defaults(self):
        cfg = AlembicMigrationConfig(database_url="postgresql+asyncpg://localhost/db")
        assert cfg.database_url == "postgresql+asyncpg://localhost/db"
        assert cfg.script_location == "./migrations"
        assert cfg.version_table == "alembic_version"
        assert cfg.target_metadata is None
        assert cfg.extra_context == {}

    def test_custom_values(self):
        cfg = AlembicMigrationConfig(
            database_url="sqlite+aiosqlite:///test.db",
            script_location="/custom/migrations",
            version_table="my_version",
            file_template="%%(rev)s_%%(slug)s",
        )
        assert cfg.script_location == "/custom/migrations"
        assert cfg.version_table == "my_version"
        assert cfg.file_template == "%%(rev)s_%%(slug)s"

    def test_frozen(self):
        cfg = AlembicMigrationConfig(database_url="sqlite:///:memory:")
        with pytest.raises(AttributeError):
            cfg.database_url = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _async_url_to_sync
# ---------------------------------------------------------------------------


class TestAsyncUrlToSync:
    def test_postgresql_asyncpg(self):
        assert _async_url_to_sync("postgresql+asyncpg://host/db") == "postgresql://host/db"

    def test_sqlite_aiosqlite(self):
        assert _async_url_to_sync("sqlite+aiosqlite:///test.db") == "sqlite:///test.db"

    def test_mysql_aiomysql(self):
        assert _async_url_to_sync("mysql+aiomysql://host/db") == "mysql+pymysql://host/db"

    def test_already_sync(self):
        assert _async_url_to_sync("postgresql://host/db") == "postgresql://host/db"

    def test_unknown_driver(self):
        assert _async_url_to_sync("oracle://host/db") == "oracle://host/db"


# ---------------------------------------------------------------------------
# create_alembic_config
# ---------------------------------------------------------------------------


class TestCreateAlembicConfig:
    def test_creates_config(self):
        migration_cfg = AlembicMigrationConfig(
            database_url="postgresql+asyncpg://localhost/db",
            script_location="/migrations",
        )
        alembic_cfg = create_alembic_config(migration_cfg)
        assert alembic_cfg.get_main_option("script_location") == "/migrations"
        assert alembic_cfg.get_main_option("sqlalchemy.url") == "postgresql://localhost/db"
        assert alembic_cfg.get_main_option("version_table") == "alembic_version"

    def test_async_url_converted(self):
        migration_cfg = AlembicMigrationConfig(
            database_url="sqlite+aiosqlite:///test.db",
        )
        alembic_cfg = create_alembic_config(migration_cfg)
        assert alembic_cfg.get_main_option("sqlalchemy.url") == "sqlite:///test.db"


# ---------------------------------------------------------------------------
# run_upgrade_to_head / run_downgrade / stamp_head
# ---------------------------------------------------------------------------


class TestRunUpgrade:
    @pytest.mark.asyncio
    async def test_calls_alembic_upgrade(self):
        cfg = AlembicMigrationConfig(database_url="sqlite:///:memory:")
        with patch("shared.sqlalchemy_async.migrations.create_alembic_config") as mock_create:
            mock_alembic_cfg = MagicMock()
            mock_create.return_value = mock_alembic_cfg
            with patch("alembic.command.upgrade") as mock_upgrade:
                await run_upgrade_to_head(cfg)
                mock_upgrade.assert_called_once_with(mock_alembic_cfg, "head")


class TestRunDowngrade:
    @pytest.mark.asyncio
    async def test_calls_alembic_downgrade(self):
        cfg = AlembicMigrationConfig(database_url="sqlite:///:memory:")
        with patch("shared.sqlalchemy_async.migrations.create_alembic_config") as mock_create:
            mock_alembic_cfg = MagicMock()
            mock_create.return_value = mock_alembic_cfg
            with patch("alembic.command.downgrade") as mock_downgrade:
                await run_downgrade(cfg, "-1")
                mock_downgrade.assert_called_once_with(mock_alembic_cfg, "-1")

    @pytest.mark.asyncio
    async def test_default_revision(self):
        cfg = AlembicMigrationConfig(database_url="sqlite:///:memory:")
        with (
            patch("shared.sqlalchemy_async.migrations.create_alembic_config"),
            patch("alembic.command.downgrade") as mock_downgrade,
        ):
            await run_downgrade(cfg)
            mock_downgrade.assert_called_once()
            assert mock_downgrade.call_args[0][1] == "-1"


class TestStampHead:
    def test_calls_alembic_stamp(self):
        cfg = AlembicMigrationConfig(database_url="sqlite:///:memory:")
        with patch("shared.sqlalchemy_async.migrations.create_alembic_config") as mock_create:
            mock_alembic_cfg = MagicMock()
            mock_create.return_value = mock_alembic_cfg
            with patch("alembic.command.stamp") as mock_stamp:
                stamp_head(cfg)
                mock_stamp.assert_called_once_with(mock_alembic_cfg, "head")


# ---------------------------------------------------------------------------
# generate_migration_scaffold
# ---------------------------------------------------------------------------


class TestGenerateMigrationScaffold:
    def test_creates_directories_and_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "migrations"
            env_py = generate_migration_scaffold(base_dir)

            assert env_py.exists()
            assert (base_dir / "versions").is_dir()
            assert (base_dir / "script.py.mako").exists()

    def test_env_py_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "migrations"
            env_py = generate_migration_scaffold(base_dir)
            content = env_py.read_text()
            assert "run_migrations_offline" in content
            assert "run_migrations_online" in content
            assert "target_metadata" in content

    def test_does_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "migrations"
            base_dir.mkdir()
            existing = base_dir / "env.py"
            existing.write_text("# custom env")

            generate_migration_scaffold(base_dir)
            assert existing.read_text() == "# custom env"

    def test_mako_template_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "migrations"
            generate_migration_scaffold(base_dir)
            mako = base_dir / "script.py.mako"
            content = mako.read_text()
            assert "revision" in content
            assert "def upgrade" in content
            assert "def downgrade" in content
