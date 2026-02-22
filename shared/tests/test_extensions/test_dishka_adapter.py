"""Tests for the Dishka DI adapter module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to reset the cached availability between tests
import shared.extensions.dishka_adapter as _mod
from shared.extensions.dishka_adapter import (
    DishkaContainerAdapter,
    DishkaFastAPIMiddleware,
    _require_dishka,
    create_dishka_fastapi_middleware,
    dishka_dependency,
    is_dishka_available,
)


@pytest.fixture(autouse=True)
def _reset_dishka_cache() -> None:
    """Reset the module-level availability cache between tests."""
    _mod._dishka_available = None


# ======================================================================
# TestAvailabilityCheck
# ======================================================================


class TestAvailabilityCheck:
    def test_is_dishka_available_returns_bool(self) -> None:
        result = is_dishka_available()
        assert isinstance(result, bool)

    def test_is_dishka_available_cached(self) -> None:
        """Second call uses cached value (no import)."""
        first = is_dishka_available()
        second = is_dishka_available()
        assert first == second

    def test_availability_when_not_installed(self) -> None:
        """When dishka is not importable, returns False."""
        with patch.dict("sys.modules", {"dishka": None}):
            _mod._dishka_available = None
            # Force a fresh import check

            with patch("builtins.__import__", side_effect=ImportError):
                _mod._dishka_available = None
                assert is_dishka_available() is False

    def test_require_dishka_when_unavailable(self) -> None:
        _mod._dishka_available = False
        with pytest.raises(ImportError, match="dishka"):
            _require_dishka()


# ======================================================================
# TestDishkaContainerAdapter (with mocked dishka)
# ======================================================================


class TestDishkaContainerAdapter:
    @pytest.fixture()
    def _enable_dishka(self) -> None:
        _mod._dishka_available = True

    @pytest.fixture()
    def mock_container(self) -> MagicMock:
        container = AsyncMock()
        container.get = AsyncMock(return_value="resolved_value")
        container.close = AsyncMock()
        return container

    def test_raises_when_dishka_unavailable(self) -> None:
        _mod._dishka_available = False
        with pytest.raises(ImportError, match="dishka"):
            DishkaContainerAdapter(MagicMock())

    @pytest.mark.usefixtures("_enable_dishka")
    def test_inner_property(self, mock_container: MagicMock) -> None:
        adapter = DishkaContainerAdapter(mock_container)
        assert adapter.inner is mock_container

    @pytest.mark.usefixtures("_enable_dishka")
    async def test_resolve_async(self, mock_container: AsyncMock) -> None:
        adapter = DishkaContainerAdapter(mock_container)

        class IService:
            pass

        mock_container.get = AsyncMock(return_value="svc_instance")
        result = await adapter.resolve_async(IService)
        assert result == "svc_instance"
        mock_container.get.assert_awaited_once_with(IService)

    @pytest.mark.usefixtures("_enable_dishka")
    def test_resolve_sync(self, mock_container: MagicMock) -> None:
        mock_container.get = MagicMock(return_value="sync_val")
        adapter = DishkaContainerAdapter(mock_container)
        result = adapter.resolve_sync(str)
        assert result == "sync_val"

    @pytest.mark.usefixtures("_enable_dishka")
    async def test_close(self, mock_container: AsyncMock) -> None:
        adapter = DishkaContainerAdapter(mock_container)
        await adapter.close()
        mock_container.close.assert_awaited_once()


# ======================================================================
# TestDishkaFastAPIMiddleware
# ======================================================================


class TestDishkaFastAPIMiddleware:
    @pytest.fixture()
    def _enable_dishka(self) -> None:
        _mod._dishka_available = True

    def test_raises_when_dishka_unavailable(self) -> None:
        _mod._dishka_available = False
        with pytest.raises(ImportError, match="dishka"):
            DishkaFastAPIMiddleware(MagicMock(), MagicMock())

    @pytest.mark.usefixtures("_enable_dishka")
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP scopes (e.g., 'lifespan') pass through directly."""
        inner_app = AsyncMock()
        container = MagicMock()
        mw = DishkaFastAPIMiddleware(inner_app, container)

        scope: dict[str, Any] = {"type": "lifespan"}
        receive = AsyncMock()
        send = AsyncMock()
        await mw(scope, receive, send)
        inner_app.assert_awaited_once_with(scope, receive, send)

    @pytest.mark.usefixtures("_enable_dishka")
    async def test_http_scope_creates_request_container(self) -> None:
        """HTTP requests create a scoped container in scope['state']."""
        inner_app = AsyncMock()
        request_container = AsyncMock()

        # Mock the container's __call__ to return an async context manager
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=request_container)
        ctx.__aexit__ = AsyncMock(return_value=False)

        container = MagicMock()
        container.return_value = ctx

        mw = DishkaFastAPIMiddleware(inner_app, container)

        scope: dict[str, Any] = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()
        await mw(scope, receive, send)

        # The request container should be stored in scope.state
        assert scope["state"]["dishka_container"] is request_container
        inner_app.assert_awaited_once()


# ======================================================================
# TestCreateDishkaFastAPIMiddleware
# ======================================================================


class TestCreateMiddleware:
    def test_raises_when_dishka_unavailable(self) -> None:
        _mod._dishka_available = False
        with pytest.raises(ImportError, match="dishka"):
            create_dishka_fastapi_middleware(MagicMock())

    def test_returns_class_when_available(self) -> None:
        _mod._dishka_available = True
        cls = create_dishka_fastapi_middleware(MagicMock())
        assert isinstance(cls, type)

    def test_returned_class_is_callable(self) -> None:
        _mod._dishka_available = True
        cls = create_dishka_fastapi_middleware(MagicMock())
        instance = cls(AsyncMock())  # pass app
        assert callable(instance)


# ======================================================================
# TestDishkaDependency
# ======================================================================


class TestDishkaDependency:
    def test_raises_when_dishka_unavailable(self) -> None:
        _mod._dishka_available = False
        with pytest.raises(ImportError, match="dishka"):
            dishka_dependency(str)

    def test_returns_callable_when_available(self) -> None:
        _mod._dishka_available = True
        dep = dishka_dependency(str)
        assert callable(dep)

    def test_dependency_name(self) -> None:
        _mod._dishka_available = True
        dep = dishka_dependency(str)
        assert "dishka_str" in dep.__name__

    async def test_dependency_resolves_from_request_state(self) -> None:
        _mod._dishka_available = True
        dep = dishka_dependency(str)

        mock_container = AsyncMock()
        mock_container.get = AsyncMock(return_value="hello")
        mock_request = MagicMock()
        mock_request.state.dishka_container = mock_container

        result = await dep(mock_request)
        assert result == "hello"
        mock_container.get.assert_awaited_once_with(str)
