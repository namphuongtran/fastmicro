"""Query types and query bus.

A *query* represents a request to read data without side-effects.
Each query type has exactly one handler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from shared.cqrs.bus import MessageBus

R = TypeVar("R")  # Return / result type
Q = TypeVar("Q", bound="Query[Any]")


@dataclass(frozen=True)
class Query(Generic[R]):
    """Base class for all queries.

    Queries are **immutable** data carriers that describe a read
    request.  The generic parameter ``R`` is the expected result type.

    Attributes:
        metadata: Optional dict for carrying cross-cutting context
            (correlation ID, tenant ID, user context, etc.).

    Example::

        @dataclass(frozen=True)
        class GetOrderById(Query[OrderDTO | None]):
            order_id: str
    """

    metadata: dict[str, Any] = field(
        default_factory=dict,
        compare=False,
        repr=False,
        kw_only=True,
    )


class QueryHandler(ABC, Generic[Q, R]):
    """Handler for a specific query type.

    Subclass and implement :meth:`handle` to process the query.

    Example::

        class GetOrderByIdHandler(QueryHandler[GetOrderById, OrderDTO | None]):
            async def handle(self, query: GetOrderById) -> OrderDTO | None:
                return await self._repo.get(query.order_id)
    """

    @abstractmethod
    async def handle(self, query: Q) -> R:
        """Execute the query and return the result.

        Args:
            query: The query to process.

        Returns:
            The query result.
        """
        ...


class QueryBus(MessageBus[Query[Any], QueryHandler[Any, Any]]):
    """Dispatches queries to their registered handlers.

    Each query type may have at most **one** handler.
    Uses copy-on-write for thread-safe lock-free reads on the hot path.

    Example::

        bus = QueryBus()
        bus.register(GetOrderById, GetOrderByIdHandler())
        order = await bus.dispatch(GetOrderById(order_id="123"))
    """

    _label: str = "query"
