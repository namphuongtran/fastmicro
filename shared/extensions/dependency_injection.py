"""Dependency injection container and utilities.

This module provides a lightweight dependency injection container
for managing service lifetimes and dependencies.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    ParamSpec,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Generator

T = TypeVar("T")
P = ParamSpec("P")


class Scope(Enum):
    """Dependency lifetime scope."""

    TRANSIENT = "transient"  # New instance every time
    SINGLETON = "singleton"  # Single instance for container lifetime
    SCOPED = "scoped"  # Single instance within a scope


@dataclass
class Depends(Generic[T]):
    """Marker for dependency injection.

    Use this as a default value for function parameters to indicate
    that the value should be injected.

    Example:
        >>> def my_service(db: IDatabase = Depends(IDatabase)):
        ...     pass
    """

    dependency: type[T]
    default_factory: type[T] | None = None


@dataclass
class Registration:
    """Internal registration data."""

    factory: Callable[[], Any]
    scope: Scope
    instance: Any = None


class ScopedContainer:
    """A scoped container for managing scoped lifetimes."""

    def __init__(self, parent: Container) -> None:
        self._parent = parent
        self._instances: dict[type, Any] = {}
        self._lock = threading.Lock()

    def resolve(self, interface: type[T]) -> T:
        """Resolve a dependency within this scope."""
        registration = self._parent._registrations.get(interface)
        if registration is None:
            raise KeyError(f"No registration found for {interface}")

        if registration.scope == Scope.SCOPED:
            with self._lock:
                if interface not in self._instances:
                    self._instances[interface] = registration.factory()
                return self._instances[interface]

        return self._parent.resolve(interface)


class Container:
    """Dependency injection container.

    A lightweight DI container that supports different lifetime scopes
    and interface-to-implementation mapping.

    Example:
        >>> container = Container()
        >>> container.register_type(PostgresDatabase, interface=IDatabase)
        >>> db = container.resolve(IDatabase)
    """

    def __init__(self) -> None:
        self._registrations: dict[type, Registration] = {}
        self._lock = threading.Lock()

    def register_instance(
        self,
        interface: type[T],
        instance: T,
    ) -> None:
        """Register an existing instance.

        Args:
            interface: The type to register.
            instance: The instance to return.
        """
        with self._lock:
            self._registrations[interface] = Registration(
                factory=lambda: instance,
                scope=Scope.SINGLETON,
                instance=instance,
            )

    def register_factory(
        self,
        implementation: type[T],
        factory: Callable[[], T],
        interface: type[T] | None = None,
        scope: Scope = Scope.TRANSIENT,
    ) -> None:
        """Register a factory function.

        Args:
            implementation: The implementation type.
            factory: Factory function to create instances.
            interface: Optional interface type.
            scope: Lifetime scope.
        """
        key = interface or implementation
        with self._lock:
            self._registrations[key] = Registration(
                factory=factory,
                scope=scope,
            )

    def register_type(
        self,
        implementation: type[T],
        interface: type[T] | None = None,
        scope: Scope = Scope.TRANSIENT,
    ) -> None:
        """Register a type for auto-instantiation.

        Args:
            implementation: The implementation type.
            interface: Optional interface type.
            scope: Lifetime scope.
        """
        key = interface or implementation
        with self._lock:
            self._registrations[key] = Registration(
                factory=lambda: implementation(),
                scope=scope,
            )

    def resolve(self, interface: type[T]) -> T:
        """Resolve a dependency.

        Args:
            interface: The type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            KeyError: If no registration found.
        """
        registration = self._registrations.get(interface)
        if registration is None:
            raise KeyError(f"No registration found for {interface}")

        if registration.scope == Scope.SINGLETON:
            with self._lock:
                if registration.instance is None:
                    registration.instance = registration.factory()
                return registration.instance

        # Transient or scoped (scoped handled by ScopedContainer)
        return registration.factory()

    def has(self, interface: type) -> bool:
        """Check if a type is registered.

        Args:
            interface: The type to check.

        Returns:
            True if registered.
        """
        return interface in self._registrations

    def clear(self) -> None:
        """Clear all registrations."""
        with self._lock:
            self._registrations.clear()

    @contextmanager
    def create_scope(self) -> Generator[ScopedContainer, None, None]:
        """Create a new scope for scoped dependencies.

        Yields:
            A scoped container.
        """
        yield ScopedContainer(self)


# Global container instance
_global_container: Container | None = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """Get the global container instance.

    Returns:
        The global Container instance.
    """
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = Container()
    return _global_container


def register(
    implementation: type[T],
    interface: type[T] | None = None,
    scope: Scope = Scope.TRANSIENT,
) -> None:
    """Register a type with the global container.

    Args:
        implementation: The implementation type.
        interface: Optional interface type.
        scope: Lifetime scope.
    """
    get_container().register_type(implementation, interface=interface, scope=scope)


def resolve(interface: type[T]) -> T:
    """Resolve a dependency from the global container.

    Args:
        interface: The type to resolve.

    Returns:
        Instance of the requested type.
    """
    return get_container().resolve(interface)


def inject(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to inject dependencies into function parameters.

    Parameters with Depends() as default will be injected from
    the global container.

    Args:
        func: Function to decorate.

    Returns:
        Decorated function with dependency injection.

    Example:
        >>> @inject
        ... def my_service(db: IDatabase = Depends(IDatabase)):
        ...     return db.query("SELECT 1")
    """
    sig = inspect.signature(func)
    
    # Find parameters with Depends defaults
    depends_params: dict[str, Depends] = {}
    for name, param in sig.parameters.items():
        if isinstance(param.default, Depends):
            depends_params[name] = param.default

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Inject dependencies not provided in kwargs
        container = get_container()
        for name, dep in depends_params.items():
            if name not in kwargs:
                try:
                    kwargs[name] = container.resolve(dep.dependency)
                except KeyError:
                    if dep.default_factory:
                        kwargs[name] = dep.default_factory()
                    else:
                        raise
        return func(*args, **kwargs)

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Inject dependencies not provided in kwargs
        container = get_container()
        for name, dep in depends_params.items():
            if name not in kwargs:
                try:
                    kwargs[name] = container.resolve(dep.dependency)
                except KeyError:
                    if dep.default_factory:
                        kwargs[name] = dep.default_factory()
                    else:
                        raise
        return await func(*args, **kwargs)  # type: ignore[misc]

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore[return-value]
    return sync_wrapper
