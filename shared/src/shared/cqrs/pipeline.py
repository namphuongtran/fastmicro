"""Pipeline behaviors for cross-cutting concerns.

Behaviors wrap the execution of a command/query handler and can
add logging, timing, validation, or any other cross-cutting logic.
They form a middleware chain similar to HTTP middleware.

Example::

    mediator = Mediator()
    mediator.add_behavior(LoggingBehavior())
    mediator.add_behavior(TimingBehavior(slow_threshold_ms=200))
"""

from __future__ import annotations

import inspect
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

R = TypeVar("R")

logger = logging.getLogger(__name__)


class PipelineBehavior(ABC):
    """Abstract pipeline behavior (middleware).

    Behaviors are executed in registration order, wrapping the
    innermost handler call.  Each behavior **must** call ``next_``
    to continue the pipeline (unless it short-circuits intentionally).

    To restrict a behavior to specific request types, override
    :meth:`applies_to` (default returns ``True`` for all requests).

    Example::

        class AuthorizationBehavior(PipelineBehavior):
            def applies_to(self, request: Any) -> bool:
                return isinstance(request, Command)  # skip queries

            async def handle(self, request, next_):
                if not request.context.is_authenticated:
                    raise ForbiddenException("Not authorized")
                return await next_(request)
    """

    def applies_to(self, request: Any) -> bool:
        """Return ``True`` if this behavior should wrap *request*.

        Override in subclasses for per-type filtering.  The default
        implementation returns ``True`` for all request types.

        Args:
            request: The command or query being dispatched.
        """
        return True

    @abstractmethod
    async def handle(
        self,
        request: Any,
        next_: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Process *request*, calling *next_* to invoke the next behavior/handler.

        Args:
            request: The command or query being dispatched.
            next_: Callable that invokes the next behavior or the final handler.

        Returns:
            The result from the handler (or a modified result).
        """
        ...


class LoggingBehavior(PipelineBehavior):
    """Logs command/query dispatch at DEBUG level and errors at ERROR level.

    Args:
        log_level: Log level for successful dispatches (default DEBUG).
    """

    def __init__(self, log_level: int = logging.DEBUG) -> None:
        self._log_level = log_level

    async def handle(
        self,
        request: Any,
        next_: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        request_name = type(request).__name__
        logger.log(self._log_level, "Dispatching %s", request_name)
        try:
            result = await next_(request)
            logger.log(self._log_level, "Completed %s", request_name)
            return result
        except Exception:
            logger.exception("Failed %s", request_name)
            raise


class TimingBehavior(PipelineBehavior):
    """Measures handler execution time.

    Logs a warning when execution exceeds *slow_threshold_ms*.

    Args:
        slow_threshold_ms: Threshold in milliseconds for a slow warning
            (default 500).
    """

    def __init__(self, slow_threshold_ms: float = 500.0) -> None:
        self._threshold = slow_threshold_ms

    async def handle(
        self,
        request: Any,
        next_: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        start = time.perf_counter()
        try:
            return await next_(request)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            request_name = type(request).__name__
            if elapsed_ms >= self._threshold:
                logger.warning(
                    "Slow %s: %.1fms (threshold: %.1fms)",
                    request_name,
                    elapsed_ms,
                    self._threshold,
                )
            else:
                logger.debug(
                    "%s completed in %.1fms",
                    request_name,
                    elapsed_ms,
                )


class ValidationBehavior(PipelineBehavior):
    """Calls a ``validate()`` method on the request if present.

    Supports both synchronous and asynchronous validation::

        @dataclass(frozen=True)
        class CreateUser(Command[str]):
            email: str

            def validate(self) -> None:
                if "@" not in self.email:
                    raise ValueError("Invalid email")

        @dataclass(frozen=True)
        class CreateUniqueUser(Command[str]):
            email: str

            async def validate(self) -> None:
                if await email_exists(self.email):
                    raise ValueError("Email already in use")
    """

    async def handle(
        self,
        request: Any,
        next_: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        validate = getattr(request, "validate", None)
        if callable(validate):
            result = validate()
            if inspect.isawaitable(result):
                await result
        return await next_(request)
