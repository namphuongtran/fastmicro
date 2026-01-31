"""
Shared library for enterprise Python microservices.

This package provides common utilities, patterns, and abstractions
for building robust microservices including:

- **exceptions**: Standardized exception hierarchy for HTTP, database, validation
- **constants**: HTTP status codes, environment detection, regex patterns
- **utils**: Datetime handling, JSON serialization, string manipulation, validation

Example:
    >>> from shared.exceptions import NotFoundError, ValidationException
    >>> from shared.constants import HTTPStatus, Environment
    >>> from shared.utils import now_utc, serialize_json, slugify
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export commonly used items for convenience
from shared.constants import Environment, HTTPStatus, Patterns
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
]
