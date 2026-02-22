"""Dishka DI adapter – optional bridge to the Dishka async DI framework.

This module provides integration between the shared library's
:class:`~shared.extensions.dependency_injection.Container` and the
`Dishka <https://pypi.org/project/dishka/>`_ DI container, plus
FastAPI request-scoped dependency helpers.

**Dishka is an optional dependency.**  All public symbols gracefully
degrade when ``dishka`` is not installed — :func:`is_dishka_available`
returns ``False`` and the adapter constructors raise
:class:`ImportError` with a helpful message.

Quick start::

    from dishka import make_async_container, Provider, Scope
    from shared.extensions.dishka_adapter import (
        DishkaContainerAdapter,
        create_dishka_fastapi_middleware,
    )

    # 1. Configure Dishka as normal
    provider = Provider()
    provider.provide(MyRepo, scope=Scope.REQUEST)
    dishka_container = make_async_container(provider)

    # 2. Wrap in our adapter for shared-library-compatible API
    adapter = DishkaContainerAdapter(dishka_container)
    user_repo = await adapter.resolve_async(IUserRepo)

    # 3. FastAPI integration
    app = FastAPI()
    app.add_middleware(create_dishka_fastapi_middleware(dishka_container))
"""

from __future__ import annotations

import inspect
import threading
from typing import TYPE_CHECKING, Any, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

_dishka_available: bool | None = None
_check_lock = threading.Lock()


def is_dishka_available() -> bool:
    """Check whether the ``dishka`` package is importable.

    Returns:
        ``True`` if Dishka is installed, ``False`` otherwise.
    """
    global _dishka_available
    if _dishka_available is None:
        with _check_lock:
            if _dishka_available is None:
                try:
                    import dishka  # noqa: F401

                    _dishka_available = True
                except ImportError:
                    _dishka_available = False
    return _dishka_available


def _require_dishka() -> None:
    """Raise :class:`ImportError` if dishka is not installed."""
    if not is_dishka_available():
        raise ImportError(
            "The 'dishka' package is required for DishkaContainerAdapter. "
            "Install it with: pip install dishka"
        )


# ---------------------------------------------------------------------------
# DishkaContainerAdapter
# ---------------------------------------------------------------------------


class DishkaContainerAdapter:
    """Adapter that wraps a Dishka ``AsyncContainer`` with a
    shared-library-compatible interface.

    This allows applications to use Dishka for advanced DI features
    (auto-wiring, provider scoping, request-scoped lifetimes) while
    keeping the rest of the codebase decoupled from any specific DI
    framework.

    Args:
        dishka_container: A ``dishka.AsyncContainer`` (or
            ``dishka.Container`` — the adapter accepts both).

    Raises:
        ImportError: If ``dishka`` is not installed.

    Example::

        from dishka import make_async_container, Provider, Scope
        from shared.extensions.dishka_adapter import DishkaContainerAdapter

        provider = Provider()
        provider.provide(lambda: PostgresRepo(), scope=Scope.APP)
        container = make_async_container(provider)

        adapter = DishkaContainerAdapter(container)
        repo = await adapter.resolve_async(IRepo)
    """

    def __init__(self, dishka_container: Any) -> None:
        _require_dishka()
        self._container = dishka_container

    @property
    def inner(self) -> Any:
        """Access the underlying Dishka container."""
        return self._container

    async def resolve_async(self, interface: type[T]) -> T:
        """Resolve a dependency asynchronously via Dishka.

        Args:
            interface: The type to resolve.

        Returns:
            The resolved instance.
        """
        return await self._container.get(interface)

    def resolve_sync(self, interface: type[T]) -> T:
        """Resolve a dependency synchronously (for sync containers).

        Args:
            interface: The type to resolve.

        Returns:
            The resolved instance.

        Raises:
            TypeError: If the underlying container returns a coroutine
                (i.e. it is an async container — use
                :meth:`resolve_async` instead).
            AttributeError: If the container does not support sync ``get``.
        """
        result = self._container.get(interface)
        if inspect.isawaitable(result):
            raise TypeError(
                "Cannot resolve synchronously from an async container. "
                "Use resolve_async() instead."
            )
        return result

    async def close(self) -> None:
        """Close the underlying Dishka container and release resources."""
        await self._container.close()


# ---------------------------------------------------------------------------
# FastAPI integration helpers
# ---------------------------------------------------------------------------


class DishkaFastAPIMiddleware:
    """ASGI middleware that creates a Dishka request scope per request.

    For each incoming request a new Dishka request scope is entered,
    attached to ``request.state.dishka_container``, and closed after
    the response.

    Args:
        app: The ASGI application.
        container: A Dishka ``AsyncContainer``.

    Raises:
        ImportError: If ``dishka`` is not installed.
    """

    def __init__(self, app: Any, container: Any) -> None:
        _require_dishka()
        self._app = app
        self._container = container
        # Cache the Dishka Scope.REQUEST value to avoid per-request import
        try:
            from dishka import Scope as DishkaScope

            self._request_scope = DishkaScope.REQUEST
        except ImportError:
            # Fallback: the container's __call__ may accept scope kwarg
            # directly.  This allows tests that fake is_dishka_available()
            # without having dishka installed.
            self._request_scope = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        if self._request_scope is not None:
            ctx = self._container(scope=self._request_scope)
        else:
            ctx = self._container()
        async with ctx as request_container:
            # Store reference in ASGI scope for downstream access
            scope.setdefault("state", {})
            scope["state"]["dishka_container"] = request_container
            await self._app(scope, receive, send)


def create_dishka_fastapi_middleware(container: Any) -> type:
    """Create a Starlette/FastAPI middleware class bound to *container*.

    Usage::

        from shared.extensions.dishka_adapter import create_dishka_fastapi_middleware

        app = FastAPI()
        middleware_cls = create_dishka_fastapi_middleware(dishka_container)
        app.add_middleware(middleware_cls)

    Args:
        container: A Dishka ``AsyncContainer``.

    Returns:
        A middleware class that can be passed to ``app.add_middleware()``.

    Raises:
        ImportError: If ``dishka`` is not installed.
    """
    _require_dishka()

    class _BoundMiddleware:
        """Pre-bound Dishka middleware (closure over *container*)."""

        def __init__(self, app: Any) -> None:
            self._inner = DishkaFastAPIMiddleware(app, container)

        async def __call__(
            self,
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            await self._inner(scope, receive, send)

    return _BoundMiddleware


# ---------------------------------------------------------------------------
# Dishka FastAPI dependency helper
# ---------------------------------------------------------------------------


def dishka_dependency(interface: type[T]) -> Any:
    """Create a FastAPI ``Depends()`` that resolves *interface* from the
    Dishka request container stored in ``request.state``.

    Usage::

        from shared.extensions.dishka_adapter import dishka_dependency

        @app.get("/users")
        async def list_users(
            repo: IUserRepo = Depends(dishka_dependency(IUserRepo)),
        ):
            return await repo.get_all()

    Args:
        interface: The type to resolve from Dishka.

    Returns:
        A FastAPI dependency callable.

    Raises:
        ImportError: If ``dishka`` is not installed.
    """
    _require_dishka()

    async def _resolve(request: Any) -> T:
        container = request.state.dishka_container
        return await container.get(interface)

    # Give the dependency a meaningful name for FastAPI docs
    _resolve.__name__ = f"dishka_{interface.__name__}"
    _resolve.__qualname__ = f"dishka_{interface.__qualname__}"
    return _resolve
