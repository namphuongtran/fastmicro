"""Tests for shared.fastapi_utils.lifespan module.

This module tests FastAPI lifespan management.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.fastapi_utils.lifespan import (
    LifespanManager,
    create_lifespan,
    register_shutdown_handler,
    register_startup_handler,
)


class TestLifespanManager:
    """Tests for LifespanManager class."""

    def test_create_lifespan_manager(self) -> None:
        """Should create lifespan manager."""
        manager = LifespanManager()

        assert manager is not None
        assert len(manager.startup_handlers) == 0
        assert len(manager.shutdown_handlers) == 0

    def test_register_startup_handler(self) -> None:
        """Should register startup handler."""
        manager = LifespanManager()

        async def startup():
            pass

        manager.add_startup_handler(startup)

        assert len(manager.startup_handlers) == 1

    def test_register_shutdown_handler(self) -> None:
        """Should register shutdown handler."""
        manager = LifespanManager()

        async def shutdown():
            pass

        manager.add_shutdown_handler(shutdown)

        assert len(manager.shutdown_handlers) == 1

    def test_register_multiple_handlers(self) -> None:
        """Should support multiple handlers."""
        manager = LifespanManager()

        async def startup1():
            pass

        async def startup2():
            pass

        async def shutdown1():
            pass

        manager.add_startup_handler(startup1)
        manager.add_startup_handler(startup2)
        manager.add_shutdown_handler(shutdown1)

        assert len(manager.startup_handlers) == 2
        assert len(manager.shutdown_handlers) == 1

    @pytest.mark.asyncio
    async def test_startup_handlers_called(self) -> None:
        """Should call all startup handlers."""
        manager = LifespanManager()
        startup_called = []

        async def startup1():
            startup_called.append("startup1")

        async def startup2():
            startup_called.append("startup2")

        manager.add_startup_handler(startup1)
        manager.add_startup_handler(startup2)

        await manager.startup()

        assert startup_called == ["startup1", "startup2"]

    @pytest.mark.asyncio
    async def test_shutdown_handlers_called(self) -> None:
        """Should call all shutdown handlers."""
        manager = LifespanManager()
        shutdown_called = []

        async def shutdown1():
            shutdown_called.append("shutdown1")

        async def shutdown2():
            shutdown_called.append("shutdown2")

        manager.add_shutdown_handler(shutdown1)
        manager.add_shutdown_handler(shutdown2)

        await manager.shutdown()

        # Shutdown handlers are called in reverse order
        assert "shutdown1" in shutdown_called
        assert "shutdown2" in shutdown_called


class TestCreateLifespan:
    """Tests for create_lifespan function."""

    def test_create_lifespan_context_manager(self) -> None:
        """Should create lifespan context manager."""
        manager = LifespanManager()
        lifespan = create_lifespan(manager)

        assert callable(lifespan)

    def test_lifespan_with_app(self) -> None:
        """Should work with FastAPI app."""
        manager = LifespanManager()
        startup_called = []
        shutdown_called = []

        async def startup():
            startup_called.append(True)

        async def shutdown():
            shutdown_called.append(True)

        manager.add_startup_handler(startup)
        manager.add_shutdown_handler(shutdown)

        app = FastAPI(lifespan=create_lifespan(manager))

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            # Startup should have been called
            assert len(startup_called) == 1

        # After context exit, shutdown should have been called
        assert len(shutdown_called) == 1


class TestRegisterHandlerFunctions:
    """Tests for register_startup_handler and register_shutdown_handler."""

    def test_register_startup_handler_function(self) -> None:
        """Should register startup handler with decorator pattern."""
        app = FastAPI()
        handlers = []

        @register_startup_handler(app)
        async def my_startup():
            handlers.append("started")

        # Handler should be registered
        assert len(app.router.on_startup) >= 1

    def test_register_shutdown_handler_function(self) -> None:
        """Should register shutdown handler with decorator pattern."""
        app = FastAPI()

        @register_shutdown_handler(app)
        async def my_shutdown():
            pass

        # Handler should be registered
        assert len(app.router.on_shutdown) >= 1
