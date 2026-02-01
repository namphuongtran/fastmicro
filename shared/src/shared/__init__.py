"""
Shared library for enterprise Python microservices.

This package provides common utilities, patterns, and abstractions
for building robust microservices including:

- **exceptions**: Standardized exception hierarchy for HTTP, database, validation
- **constants**: HTTP status codes, environment detection, regex patterns
- **utils**: Datetime handling, JSON serialization, string manipulation, validation
- **observability**: Structured logging, tracing, metrics, health checks
- **dbs**: Repository pattern, Unit of Work, database utilities
- **extensions**: Decorators, dependency injection, middleware patterns

Example:
    >>> from shared.exceptions import NotFoundError, ValidationException
    >>> from shared.constants import HTTPStatus, Environment
    >>> from shared.utils import now_utc, serialize_json, slugify
    >>> from shared.observability import get_logger, configure_logging
    >>> from shared.dbs import InMemoryRepository, PageRequest
    >>> from shared.extensions import retry, cache, Container, Depends
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export commonly used items for convenience
# Application Layer Patterns
from shared.application import (
    BaseReadService,
    BaseService,
    BaseWriteService,
    ConflictError,
    CRUDService,
    NotFoundError,
    ServiceContext,
    ServiceError,
)
from shared.application import (
    ValidationError as ServiceValidationError,
)
from shared.constants import Environment, HTTPStatus, Patterns
from shared.dbs import (
    AbstractRepository,
    AbstractUnitOfWork,
    Filter,
    FilterOperator,
    InMemoryRepository,
    InMemoryUnitOfWork,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)

# DDD Building Blocks
from shared.ddd import (
    AggregateRoot,
    DomainEvent,
    DomainEventHandler,
    Entity,
    EntityId,
    EventDispatcher,
    ValueObject,
)
from shared.exceptions import (
    BadGatewayException,
    BadRequestException,
    BaseServiceException,
    ConflictException,
    ConnectionException,
    DatabaseException,
    ErrorSeverity,
    FieldError,
    ForbiddenException,
    GatewayTimeoutException,
    HTTPException,
    IntegrityException,
    InternalServerException,
    MethodNotAllowedException,
    NotFoundException,
    QueryException,
    RateLimitException,
    ServiceUnavailableException,
    TimeoutException,
    TransactionException,
    UnauthorizedException,
    UnprocessableEntityException,
    ValidationException,
)
from shared.extensions import (
    # Dependency Injection
    Container,
    Depends,
    Scope,
    cache,
    deprecated,
    get_container,
    inject,
    log_calls,
    rate_limit,
    register,
    resolve,
    # Decorators
    retry,
    singleton,
    timeout,
    validate_args,
)
from shared.observability import (
    CorrelationIdFilter,
    # Metrics
    Counter,
    Gauge,
    HealthCheck,
    HealthCheckResult,
    # Health
    HealthStatus,
    Histogram,
    # Logging
    JSONFormatter,
    MetricsRegistry,
    Span,
    # Tracing
    SpanKind,
    TracingConfig,
    check_liveness,
    check_readiness,
    configure_logging,
    configure_metrics,
    configure_tracing,
    create_health_check,
    create_span,
    extract_context,
    generate_correlation_id,
    get_correlation_id,
    get_current_span,
    get_health_status,
    get_logger,
    get_metrics_registry,
    get_trace_id,
    inject_context,
    register_health_check,
    set_correlation_id,
    timed,
    traced,
    with_context,
)
from shared.utils import (
    CustomJSONEncoder,
    ValidationResult,
    camel_to_snake,
    deserialize_json,
    end_of_day,
    format_iso8601,
    format_relative_time,
    generate_random_string,
    get_date_range,
    is_business_day,
    is_valid_email,
    is_valid_url,
    is_valid_uuid,
    mask_sensitive,
    now_utc,
    parse_iso8601,
    pluralize,
    safe_serialize,
    sanitize_filename,
    sanitize_html,
    serialize_json,
    slugify,
    snake_to_camel,
    start_of_day,
    truncate,
    utc_timestamp,
    validate_length,
    validate_range,
    validate_required,
)

__all__ = [
    # Version
    "__version__",
    # Exceptions
    "BaseServiceException",
    "ErrorSeverity",
    "HTTPException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "MethodNotAllowedException",
    "ConflictException",
    "UnprocessableEntityException",
    "RateLimitException",
    "InternalServerException",
    "BadGatewayException",
    "ServiceUnavailableException",
    "GatewayTimeoutException",
    "DatabaseException",
    "ConnectionException",
    "QueryException",
    "IntegrityException",
    "TransactionException",
    "TimeoutException",
    "ValidationException",
    "FieldError",
    # Constants
    "HTTPStatus",
    "Environment",
    "Patterns",
    # Database Patterns
    "FilterOperator",
    "OrderDirection",
    "Filter",
    "OrderBy",
    "PageRequest",
    "PageResponse",
    "AbstractRepository",
    "InMemoryRepository",
    "AbstractUnitOfWork",
    "InMemoryUnitOfWork",
    # Observability - Logging
    "JSONFormatter",
    "CorrelationIdFilter",
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "with_context",
    "get_logger",
    "configure_logging",
    # Observability - Tracing
    "SpanKind",
    "TracingConfig",
    "Span",
    "configure_tracing",
    "get_current_span",
    "get_trace_id",
    "create_span",
    "inject_context",
    "extract_context",
    "traced",
    # Observability - Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "get_metrics_registry",
    "configure_metrics",
    "timed",
    # Observability - Health
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "register_health_check",
    "create_health_check",
    "check_liveness",
    "check_readiness",
    "get_health_status",
    # Utils
    "now_utc",
    "utc_timestamp",
    "format_iso8601",
    "parse_iso8601",
    "format_relative_time",
    "start_of_day",
    "end_of_day",
    "is_business_day",
    "get_date_range",
    "CustomJSONEncoder",
    "serialize_json",
    "deserialize_json",
    "safe_serialize",
    "slugify",
    "truncate",
    "camel_to_snake",
    "snake_to_camel",
    "generate_random_string",
    "mask_sensitive",
    "sanitize_filename",
    "pluralize",
    "ValidationResult",
    "is_valid_email",
    "is_valid_url",
    "is_valid_uuid",
    "validate_required",
    "validate_length",
    "validate_range",
    "sanitize_html",
    # Extensions - Decorators
    "retry",
    "cache",
    "rate_limit",
    "timeout",
    "deprecated",
    "log_calls",
    "validate_args",
    "singleton",
    # Extensions - Dependency Injection
    "Container",
    "Scope",
    "Depends",
    "inject",
    "get_container",
    "register",
    "resolve",
    # DDD Building Blocks
    "Entity",
    "AggregateRoot",
    "EntityId",
    "ValueObject",
    "DomainEvent",
    "DomainEventHandler",
    "EventDispatcher",
    # Application Layer Patterns
    "BaseService",
    "BaseReadService",
    "BaseWriteService",
    "CRUDService",
    "ServiceContext",
    "ServiceError",
    "ServiceValidationError",
    "ConflictError",
]
