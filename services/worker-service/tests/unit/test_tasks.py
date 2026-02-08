"""Unit tests for worker-service tasks and worker configuration."""

from __future__ import annotations

import pytest

from worker_service.tasks.outbox_relay import process_outbox
from worker_service.tasks.cleanup import cleanup_expired_sessions
from worker_service.worker import WorkerSettings, startup, shutdown


# ---- Task function tests ----

class TestProcessOutbox:
    """Tests for the outbox relay task."""

    @pytest.mark.asyncio
    async def test_returns_zero_published(self):
        """Stub implementation should return 0."""
        ctx: dict = {}
        result = await process_outbox(ctx)
        assert result == 0

    @pytest.mark.asyncio
    async def test_accepts_context_dict(self):
        """Task should accept a dict context from ARQ."""
        ctx = {"settings": None, "redis": None}
        result = await process_outbox(ctx)
        assert isinstance(result, int)


class TestCleanupExpiredSessions:
    """Tests for the cleanup task."""

    @pytest.mark.asyncio
    async def test_returns_zero_cleaned(self):
        """Stub implementation should return 0."""
        ctx: dict = {}
        result = await cleanup_expired_sessions(ctx)
        assert result == 0


# ---- Worker configuration tests ----

class TestWorkerSettings:
    """Tests for ARQ WorkerSettings class."""

    def test_functions_registered(self):
        """Both task functions should be in the functions list."""
        assert process_outbox in WorkerSettings.functions
        assert cleanup_expired_sessions in WorkerSettings.functions

    def test_cron_jobs_defined(self):
        """Cron jobs should be configured."""
        assert len(WorkerSettings.cron_jobs) == 2

    def test_startup_shutdown_hooks(self):
        """Startup and shutdown hooks should be set."""
        assert WorkerSettings.on_startup is startup
        assert WorkerSettings.on_shutdown is shutdown


# ---- Startup / shutdown hooks ----

class TestWorkerHooks:
    """Tests for startup and shutdown hooks."""

    @pytest.mark.asyncio
    async def test_startup_populates_settings(self):
        """startup hook should store settings in context."""
        ctx: dict = {}
        await startup(ctx)
        assert "settings" in ctx

    @pytest.mark.asyncio
    async def test_shutdown_does_not_raise(self):
        """shutdown hook should complete without error."""
        ctx: dict = {}
        await shutdown(ctx)
