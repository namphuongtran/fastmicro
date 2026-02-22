"""Container protocol — shared interface for DI containers.

Defines a structural protocol that both the lightweight built-in
:class:`~shared.extensions.dependency_injection.Container` and the
:class:`~shared.extensions.dishka_adapter.DishkaContainerAdapter`
satisfy, enabling framework-agnostic dependency resolution.

Usage::

    from shared.extensions.container_protocol import ContainerProtocol

    async def bootstrap(container: ContainerProtocol) -> None:
        repo = await container.resolve_async(IUserRepo)
        ...
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ContainerProtocol(Protocol):
    """Structural protocol satisfied by all shared-library DI containers.

    Both the lightweight :class:`Container` and the
    :class:`DishkaContainerAdapter` expose at least :meth:`resolve_async`
    for async resolution and :meth:`resolve_sync` for synchronous
    resolution.

    This protocol enables writing framework-agnostic code that
    depends only on the capability to resolve typed dependencies.
    """

    async def resolve_async(self, interface: type[T]) -> T:
        """Resolve a dependency asynchronously.

        Args:
            interface: The type to resolve.

        Returns:
            The resolved instance.
        """
        ...

    def resolve_sync(self, interface: type[T]) -> T:
        """Resolve a dependency synchronously.

        Args:
            interface: The type to resolve.

        Returns:
            The resolved instance.
        """
        ...
