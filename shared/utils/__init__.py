"""
Shared utilities for common operations.

This package provides utility modules for:
- datetime: Timezone handling, formatting, parsing
- serialization: JSON serialization with custom type support
- strings: String manipulation and sanitization
- validation: Input validation and sanitization

Example:
    >>> from shared.utils import now_utc, serialize_json, slugify
    >>> from shared.utils.validation import is_valid_email
"""

from __future__ import annotations

from shared.utils.datetime import (
    end_of_day,
    format_iso8601,
    format_relative_time,
    get_date_range,
    is_business_day,
    now_utc,
    parse_iso8601,
    start_of_day,
    utc_timestamp,
)
from shared.utils.serialization import (
    CustomJSONEncoder,
    deserialize_json,
    safe_serialize,
    serialize_json,
)
from shared.utils.strings import (
    camel_to_snake,
    generate_random_string,
    mask_sensitive,
    pluralize,
    sanitize_filename,
    slugify,
    snake_to_camel,
    truncate,
)
from shared.utils.validation import (
    ValidationResult,
    is_valid_email,
    is_valid_url,
    is_valid_uuid,
    sanitize_html,
    validate_length,
    validate_range,
    validate_required,
)

__all__ = [
    # datetime
    "now_utc",
    "utc_timestamp",
    "format_iso8601",
    "parse_iso8601",
    "format_relative_time",
    "start_of_day",
    "end_of_day",
    "is_business_day",
    "get_date_range",
    # serialization
    "CustomJSONEncoder",
    "serialize_json",
    "deserialize_json",
    "safe_serialize",
    # strings
    "slugify",
    "truncate",
    "camel_to_snake",
    "snake_to_camel",
    "generate_random_string",
    "mask_sensitive",
    "sanitize_filename",
    "pluralize",
    # validation
    "ValidationResult",
    "is_valid_email",
    "is_valid_url",
    "is_valid_uuid",
    "validate_required",
    "validate_length",
    "validate_range",
    "sanitize_html",
]
