"""FastAPI lifespan management utilities.

This module provides utilities for managing application lifecycle
events (startup and shutdown) in a clean and testable way.

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi_utils.lifespan import LifespanManager, create_lifespan
    >>> manager = LifespanManager()
    >>> @manager.on_startup
    ... async def init_db():
    ...     await database.connect()
    >>> app = FastAPI(lifespan=create_lifespan(manager))
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import FastAPI

# Type for async handler functions
AsyncHandler = Callable[[], Awaitable[None]]
F = TypeVar("F", bound=AsyncHandler)


class LifespanManager:
    """Manages application startup and shutdown handlers.
    
    This class provides a clean way to register and manage
    lifecycle handlers for FastAPI applications.
    
    Example:
        >>> manager = LifespanManager()
        >>> manager.add_startup_handler(init_database)
        >>> manager.add_shutdown_handler(close_database)
    """

    def __init__(self) -> None:
        """Initialize the lifespan manager."""
        self._startup_handlers: list[AsyncHandler] = []
        self._shutdown_handlers: list[AsyncHandler] = []

    @property
    def startup_handlers(self) -> list[AsyncHandler]:
        """Get registered startup handlers."""
        return self._startup_handlers.copy()

    @property
    def shutdown_handlers(self) -> list[AsyncHandler]:
        """Get registered shutdown handlers."""
        return self._shutdown_handlers.copy()

    def add_startup_handler(self, handler: AsyncHandler) -> None:
        """Add a startup handler.
        
        Args:
            handler: Async function to call on startup.
        """
        self._startup_handlers.append(handler)

    def add_shutdown_handler(self, handler: AsyncHandler) -> None:
        """Add a shutdown handler.
        
        Args:
            handler: Async function to call on shutdown.
        """
        self._shutdown_handlers.append(handler)

    def on_startup(self, func: F) -> F:
        """Decorator to register a startup handler.
        
        Args:
            func: Async function to register.
            
        Returns:
            The original function.
            
        Example:
            >>> @manager.on_startup
            ... async def init_db():
            ...     await database.connect()
        """
        self.add_startup_handler(func)
        return func

    def on_shutdown(self, func: F) -> F:
        """Decorator to register a shutdown handler.
        
        Args:
            func: Async function to register.
            
        Returns:
            The original function.
            
        Example:
            >>> @manager.on_shutdown
            ... async def close_db():
            ...     await database.disconnect()
        """
        self.add_shutdown_handler(func)
        return func

    async def startup(self) -> None:
        """Run all startup handlers in order."""
        for handler in self._startup_handlers:
            await handler()

    async def shutdown(self) -> None:
        """Run all shutdown handlers in reverse order."""
        for handler in reversed(self._shutdown_handlers):
            await handler()


def create_lifespan(manager: LifespanManager):
    """Create a lifespan context manager for FastAPI.
    
    Args:
        manager: The LifespanManager with registered handlers.
        
    Returns:
        An async context manager for FastAPI's lifespan parameter.
        
    Example:
        >>> manager = LifespanManager()
        >>> app = FastAPI(lifespan=create_lifespan(manager))
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Startup
        await manager.startup()
        yield
        # Shutdown
        await manager.shutdown()

    return lifespan


def register_startup_handler(app: FastAPI) -> Callable[[F], F]:
    """Decorator to register a startup handler with FastAPI app.
    
    Args:
        app: The FastAPI application.
        
    Returns:
        A decorator function.
        
    Example:
        >>> @register_startup_handler(app)
        ... async def init_db():
        ...     await database.connect()
    """
    def decorator(func: F) -> F:
        app.router.on_startup.append(func)
        return func
    return decorator


def register_shutdown_handler(app: FastAPI) -> Callable[[F], F]:
    """Decorator to register a shutdown handler with FastAPI app.
    
    Args:
        app: The FastAPI application.
        
    Returns:
        A decorator function.
        
    Example:
        >>> @register_shutdown_handler(app)
        ... async def close_db():
        ...     await database.disconnect()
    """
    def decorator(func: F) -> F:
        app.router.on_shutdown.append(func)
        return func
    return decorator


__all__ = [
    "LifespanManager",
    "create_lifespan",
    "register_shutdown_handler",
    "register_startup_handler",
]
