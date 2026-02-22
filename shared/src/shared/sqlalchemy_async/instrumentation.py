"""SQLAlchemy OpenTelemetry auto-instrumentation utilities.

Provides a thin wrapper around ``opentelemetry-instrumentation-sqlalchemy``
to instrument :class:`AsyncDatabaseManager` and raw ``AsyncEngine`` instances
with distributed tracing.

Usage::

    from shared.sqlalchemy_async.instrumentation import instrument_engine

    db = AsyncDatabaseManager(config)
    instrument_engine(db.engine, service_name="audit-service")

Or configure globally once at startup::

    from shared.sqlalchemy_async.instrumentation import (
        configure_sqlalchemy_instrumentation,
    )

    configure_sqlalchemy_instrumentation(
        service_name="audit-service",
        enable_commenter=True,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SQLAlchemyInstrumentationConfig:
    """Configuration for SQLAlchemy instrumentation.

    Attributes:
        service_name: OpenTelemetry service name for spans.
        enable_commenter: Append SQL comments with trace context
            (``sqlcommenter``).
        commenter_options: Options passed to sqlcommenter.
        extra_attributes: Additional span attributes.
    """

    service_name: str = "unknown-service"
    enable_commenter: bool = False
    commenter_options: dict[str, Any] = field(default_factory=dict)
    extra_attributes: dict[str, str] = field(default_factory=dict)


def instrument_engine(
    engine: Any,
    *,
    service_name: str = "unknown-service",
    enable_commenter: bool = False,
    commenter_options: dict[str, Any] | None = None,
) -> None:
    """Instrument a single SQLAlchemy engine with OpenTelemetry tracing.

    Each SQL query will produce a span with database-related attributes
    (``db.system``, ``db.statement``, etc.).

    Args:
        engine: A ``sqlalchemy.engine.Engine`` or
            ``sqlalchemy.ext.asyncio.AsyncEngine``. For async engines
            the underlying sync engine is extracted automatically.
        service_name: Logical service name for OTel spans.
        enable_commenter: Whether to append SQL comments with trace context.
        commenter_options: Additional options passed to ``sqlcommenter``.

    Raises:
        ImportError: If the instrumentation package is not installed.
    """
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ImportError as exc:
        raise ImportError(
            "opentelemetry-instrumentation-sqlalchemy is required. "
            "Install it with: pip install shared[observability]"
        ) from exc

    # AsyncEngine stores the real sync engine in .sync_engine
    sync_engine = getattr(engine, "sync_engine", engine)

    kwargs: dict[str, Any] = {
        "engine": sync_engine,
    }
    if enable_commenter:
        kwargs["enable_commenter"] = True
        if commenter_options:
            kwargs["commenter_options"] = commenter_options

    SQLAlchemyInstrumentor().instrument(**kwargs)
    logger.info(
        "SQLAlchemy engine instrumented with OpenTelemetry (service=%s)",
        service_name,
    )


def uninstrument_engine(engine: Any) -> None:
    """Remove instrumentation from an engine.

    Args:
        engine: The engine to uninstrument.
    """
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ImportError:
        return

    SQLAlchemyInstrumentor().uninstrument()
    logger.info("SQLAlchemy instrumentation removed")


_instrumented: bool = False


def configure_sqlalchemy_instrumentation(
    config: SQLAlchemyInstrumentationConfig | None = None,
    *,
    service_name: str = "unknown-service",
    enable_commenter: bool = False,
) -> None:
    """Configure global SQLAlchemy instrumentation.

    Instruments **all** new engines automatically using the
    ``SQLAlchemyInstrumentor``.  Call this once during application startup.

    Args:
        config: Optional configuration dataclass.
        service_name: Service name (ignored if *config* provided).
        enable_commenter: Enable sqlcommenter (ignored if *config* provided).

    Raises:
        ImportError: If the instrumentation package is not installed.
    """
    global _instrumented

    if _instrumented:
        logger.debug("SQLAlchemy instrumentation already configured, skipping")
        return

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ImportError as exc:
        raise ImportError(
            "opentelemetry-instrumentation-sqlalchemy is required. "
            "Install it with: pip install shared[observability]"
        ) from exc

    cfg = config or SQLAlchemyInstrumentationConfig(
        service_name=service_name,
        enable_commenter=enable_commenter,
    )

    kwargs: dict[str, Any] = {}
    if cfg.enable_commenter:
        kwargs["enable_commenter"] = True
        if cfg.commenter_options:
            kwargs["commenter_options"] = cfg.commenter_options

    SQLAlchemyInstrumentor().instrument(**kwargs)
    _instrumented = True
    logger.info(
        "Global SQLAlchemy instrumentation configured (service=%s)",
        cfg.service_name,
    )


def reset_sqlalchemy_instrumentation() -> None:
    """Uninstrument globally and reset state (useful in tests)."""
    global _instrumented

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        if _instrumented:
            SQLAlchemyInstrumentor().uninstrument()
    except ImportError:
        pass

    _instrumented = False


__all__ = [
    "SQLAlchemyInstrumentationConfig",
    "configure_sqlalchemy_instrumentation",
    "instrument_engine",
    "reset_sqlalchemy_instrumentation",
    "uninstrument_engine",
]
