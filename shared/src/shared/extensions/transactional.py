"""Transactional decorator for Unit-of-Work-managed methods.

Provides a ``@transactional`` decorator that wraps an async method in a
``SqlAlchemyUnitOfWork`` context.  Supports **nesting** via savepoints:
when called from inside an already-active UoW the decorator uses
``begin_nested()`` instead of opening a second connection.

Usage::

    from shared.extensions.transactional import transactional

    class OrderService:
        def __init__(self, db: AsyncDatabaseManager):
            self._db = db

        @transactional
        async def place_order(self, uow: SqlAlchemyUnitOfWork, dto: CreateOrderDTO) -> Order:
            repo = uow.get_repository("orders", OrderRepository)
            order = Order.from_dto(dto)
            order.add_event(OrderPlaced(order_id=order.id))
            await repo.add(order)

            bridge = EventOutboxBridge(uow.session, source="order-service")
            await bridge.collect(order)
            return order

Convention
~~~~~~~~~~
The decorated method **must** accept ``uow: SqlAlchemyUnitOfWork`` as its
first positional argument (after ``self``).  If the caller already passes a
``uow`` that is active, the decorator re-uses it (savepoint).  Otherwise it
opens a fresh UoW from ``self._db`` (or a custom ``uow_factory``).
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from shared.sqlalchemy_async.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def transactional(
    fn: Callable[..., Coroutine[Any, Any, R]] | None = None,
    *,
    auto_commit: bool = True,
) -> Any:
    """Decorator that wraps an async method in a UoW transaction.

    Parameters
    ----------
    fn:
        The async method to decorate (when used without parentheses).
    auto_commit:
        If ``True`` (default), the UoW is committed automatically when the
        method returns without error.  Set to ``False`` to require an
        explicit ``await uow.commit()``.

    Rules
    -----
    1.  The class must expose ``self._db`` (an ``AsyncDatabaseManager``)
        or ``self._uow_factory`` (a callable returning ``SqlAlchemyUnitOfWork``).
    2.  The first positional argument of the wrapped method (after ``self``)
        must be ``uow: SqlAlchemyUnitOfWork``.
    3.  If the caller supplies an **already-active** UoW, the decorator
        opens a savepoint instead of creating a new UoW.

    Example without parentheses::

        @transactional
        async def create(self, uow, dto):
            ...

    Example with options::

        @transactional(auto_commit=False)
        async def batch_import(self, uow, items):
            ...
            await uow.commit()
    """

    def decorator(
        method: Callable[..., Coroutine[Any, Any, R]],
    ) -> Callable[..., Coroutine[Any, Any, R]]:
        @functools.wraps(method)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            from shared.sqlalchemy_async.unit_of_work import SqlAlchemyUnitOfWork

            # Check if a UoW was already provided and is active
            uow: SqlAlchemyUnitOfWork | None = None
            if args and isinstance(args[0], SqlAlchemyUnitOfWork):
                uow = args[0]
                rest_args = args[1:]
            elif "uow" in kwargs and isinstance(kwargs.get("uow"), SqlAlchemyUnitOfWork):
                uow = kwargs.pop("uow")
                rest_args = args
            else:
                rest_args = args

            if uow is not None and uow.is_active:
                # Nested call - use savepoint
                async with uow.begin_nested():
                    result = await method(self, uow, *rest_args, **kwargs)
                return result

            # Create a fresh UoW
            uow = _make_uow(self)
            async with uow:
                result = await method(self, uow, *rest_args, **kwargs)
                if auto_commit:
                    await uow.commit()
                return result

        return wrapper

    if fn is not None:
        # Called without parentheses: @transactional
        return decorator(fn)
    # Called with parentheses: @transactional(auto_commit=False)
    return decorator


def _make_uow(service: Any) -> SqlAlchemyUnitOfWork:
    """Construct a ``SqlAlchemyUnitOfWork`` from the service instance."""
    from shared.sqlalchemy_async.unit_of_work import SqlAlchemyUnitOfWork

    if hasattr(service, "_uow_factory"):
        return service._uow_factory()
    if hasattr(service, "_db"):
        return SqlAlchemyUnitOfWork(service._db)
    msg = (
        f"{type(service).__name__} must have a '_db' (AsyncDatabaseManager) or "
        "'_uow_factory' attribute to use @transactional"
    )
    raise AttributeError(msg)


__all__ = [
    "transactional",
]
