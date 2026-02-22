"""Decorator for automatic audit logging of service methods.

Apply ``@audit_log`` to any async method that should emit an
:class:`AuditEvent` automatically.

Example:
    >>> from shared.audit import audit_log, AuditAction
    >>>
    >>> class OrderService:
    ...     def __init__(self, audit: AuditLogger) -> None:
    ...         self._audit = audit
    ...
    ...     @audit_log(
    ...         action=AuditAction.CREATE,
    ...         resource_type="Order",
    ...         get_resource_id=lambda result: result.id,
    ...     )
    ...     async def create_order(self, data: dict) -> Order:
    ...         ...
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from shared.audit.base import AuditAction, AuditEvent, AuditLogger

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def audit_log(
    *,
    action: AuditAction | str,
    resource_type: str,
    get_actor_id: Callable[..., str] | None = None,
    get_resource_id: Callable[..., str | None] | None = None,
    description: str = "",
    include_result: bool = False,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """Decorator that emits an audit event after the decorated method.

    The decorator looks for an ``_audit`` attribute on ``self`` to find
    the :class:`AuditLogger` instance.  If none is found the call
    proceeds without auditing (a warning is logged).

    Args:
        action: Audit action verb.
        resource_type: Type of the resource being audited.
        get_actor_id: Callable to extract actor ID from the method args.
            Receives ``(self, *args, **kwargs)`` or just ``**kwargs``.
            Defaults to ``kwargs.get("actor_id")`` or ``"system"``.
        get_resource_id: Callable to extract resource ID from the *result*
            of the decorated function (receives ``result``).
        description: Static description string.
        include_result: If ``True``, attach the serialized result as
            ``new_value`` in the audit event.

    Returns:
        Decorated async function.
    """

    def decorator(
        fn: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = await fn(*args, **kwargs)

            # Resolve audit logger from self._audit
            audit_logger: AuditLogger | None = None
            if args and hasattr(args[0], "_audit"):
                audit_logger = getattr(args[0], "_audit")

            if audit_logger is None:
                logger.warning(
                    "audit_log decorator on %s: no AuditLogger found on self._audit",
                    fn.__qualname__,
                )
                return result

            # Build event
            actor_id = "system"
            if get_actor_id is not None:
                try:
                    actor_id = get_actor_id(*args, **kwargs)
                except Exception:
                    logger.debug("Failed to extract actor_id for %s", fn.__qualname__)

            resource_id: str | None = None
            if get_resource_id is not None:
                try:
                    resource_id = get_resource_id(result)
                except Exception:
                    logger.debug("Failed to extract resource_id for %s", fn.__qualname__)

            new_value: dict[str, Any] | None = None
            if include_result and result is not None:
                try:
                    if hasattr(result, "to_dict"):
                        new_value = result.to_dict()  # type: ignore[union-attr]
                    elif hasattr(result, "model_dump"):
                        new_value = result.model_dump()  # type: ignore[union-attr]
                    elif isinstance(result, dict):
                        new_value = result  # type: ignore[assignment]
                except Exception:
                    pass

            event = AuditEvent(
                action=action,
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                description=description or f"{action} {resource_type}",
                new_value=new_value,
            )

            try:
                await audit_logger.log(event)
            except Exception:
                logger.exception("Failed to write audit event for %s", fn.__qualname__)

            return result

        return wrapper

    return decorator
