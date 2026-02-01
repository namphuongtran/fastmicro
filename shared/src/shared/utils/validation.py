"""
Input validation utilities.

This module provides common validation functions and a ValidationResult
class for composable validation logic.

Example:
    >>> from shared.utils.validation import is_valid_email, validate_required
    >>> is_valid_email("user@example.com")
    True
    >>> result = validate_required("", "email")
    >>> result.is_valid
    False
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

__all__ = [
    "ValidationResult",
    "is_valid_email",
    "is_valid_url",
    "is_valid_uuid",
    "sanitize_html",
    "validate_length",
    "validate_range",
    "validate_required",
]


# Pre-compiled regex patterns for performance
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

_URL_PATTERN = re.compile(r"^https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+.*$")

_HTML_DANGEROUS_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
    re.compile(r"data:", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    """
    Result of a validation operation.

    Supports combining multiple validation results for composable validation.

    Example:
        >>> result = ValidationResult.valid()
        >>> result.is_valid
        True
        >>> result = ValidationResult.invalid("Field is required")
        >>> result.is_valid
        False
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)

    @classmethod
    def valid(cls) -> ValidationResult:
        """Create a valid result."""
        return cls(is_valid=True, errors=[])

    @classmethod
    def invalid(cls, error: str) -> ValidationResult:
        """
        Create an invalid result with a single error.

        Args:
            error: Error message.

        Returns:
            Invalid ValidationResult.
        """
        return cls(is_valid=False, errors=[error])

    @classmethod
    def invalid_multiple(cls, errors: list[str]) -> ValidationResult:
        """
        Create an invalid result with multiple errors.

        Args:
            errors: List of error messages.

        Returns:
            Invalid ValidationResult.
        """
        return cls(is_valid=False, errors=errors)

    def combine(self, other: ValidationResult) -> ValidationResult:
        """
        Combine this result with another.

        The combined result is valid only if both are valid.
        Errors from both results are concatenated.

        Args:
            other: Another ValidationResult to combine with.

        Returns:
            Combined ValidationResult.
        """
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
        )

    def __bool__(self) -> bool:
        """Return True if valid."""
        return self.is_valid


def is_valid_email(email: str) -> bool:
    """
    Check if a string is a valid email address.

    Args:
        email: String to validate.

    Returns:
        True if valid email format.

    Example:
        >>> is_valid_email("user@example.com")
        True
        >>> is_valid_email("invalid")
        False
    """
    if not email or not email.strip():
        return False

    return bool(_EMAIL_PATTERN.match(email.strip()))


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid HTTP/HTTPS URL.

    Args:
        url: String to validate.

    Returns:
        True if valid URL format.

    Example:
        >>> is_valid_url("https://example.com")
        True
        >>> is_valid_url("not-a-url")
        False
    """
    if not url or not url.strip():
        return False

    return bool(_URL_PATTERN.match(url.strip()))


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.

    Accepts both hyphenated and non-hyphenated formats.

    Args:
        value: String to validate.

    Returns:
        True if valid UUID format.

    Example:
        >>> is_valid_uuid("12345678-1234-5678-1234-567812345678")
        True
        >>> is_valid_uuid("not-a-uuid")
        False
    """
    if not value:
        return False

    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def validate_required(
    value: Any,
    field_name: str,
) -> ValidationResult:
    """
    Validate that a value is present (not None, empty string, or whitespace).

    Note: Zero and False are considered valid values.

    Args:
        value: Value to validate.
        field_name: Name of the field for error message.

    Returns:
        ValidationResult indicating if value is present.

    Example:
        >>> validate_required("value", "email").is_valid
        True
        >>> validate_required("", "email").is_valid
        False
    """
    # Allow zero and False
    if value is not None and value != "":
        if isinstance(value, str):
            if value.strip():
                return ValidationResult.valid()
        else:
            # Non-string truthy/falsy values (including 0 and False)
            return ValidationResult.valid()

    return ValidationResult.invalid(f"{field_name} is required")


def validate_length(
    value: str,
    field_name: str,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
) -> ValidationResult:
    """
    Validate string length is within bounds.

    Args:
        value: String to validate.
        field_name: Name of the field for error message.
        min_length: Minimum allowed length.
        max_length: Maximum allowed length.

    Returns:
        ValidationResult indicating if length is valid.

    Example:
        >>> validate_length("hi", "name", min_length=5).is_valid
        False
    """
    length = len(value)

    if min_length is not None and length < min_length:
        return ValidationResult.invalid(
            f"{field_name} must be at least {min_length} characters (got {length})"
        )

    if max_length is not None and length > max_length:
        return ValidationResult.invalid(
            f"{field_name} must be at most {max_length} characters (got {length})"
        )

    return ValidationResult.valid()


def validate_range(
    value: int | float,
    field_name: str,
    *,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
) -> ValidationResult:
    """
    Validate numeric value is within bounds.

    Args:
        value: Number to validate.
        field_name: Name of the field for error message.
        min_value: Minimum allowed value.
        max_value: Maximum allowed value.

    Returns:
        ValidationResult indicating if value is valid.

    Example:
        >>> validate_range(100, "age", max_value=120).is_valid
        True
    """
    if min_value is not None and value < min_value:
        return ValidationResult.invalid(f"{field_name} must be at least {min_value} (got {value})")

    if max_value is not None and value > max_value:
        return ValidationResult.invalid(f"{field_name} must be at most {max_value} (got {value})")

    return ValidationResult.valid()


def sanitize_html(content: str) -> str:
    """
    Remove potentially dangerous HTML content.

    Removes script tags, event handlers, and javascript: URLs.
    This is a basic sanitizer - for production use, consider
    a dedicated library like bleach.

    Args:
        content: HTML content to sanitize.

    Returns:
        Sanitized content.

    Example:
        >>> sanitize_html("<script>alert('xss')</script>Hello")
        'Hello'
    """
    if not content:
        return ""

    result = content

    # Remove dangerous patterns
    for pattern in _HTML_DANGEROUS_PATTERNS:
        result = pattern.sub("", result)

    # Remove remaining tags that had dangerous attributes
    # This is a simple approach - for comprehensive sanitization,
    # use a dedicated library like bleach
    result = re.sub(r"<[^>]*>", lambda m: _sanitize_tag(m.group(0)), result)

    return result.strip()


def _sanitize_tag(tag: str) -> str:
    """Helper to sanitize individual HTML tags."""
    # Remove event handlers
    tag = re.sub(r"\s+on\w+\s*=\s*['\"][^'\"]*['\"]", "", tag, flags=re.IGNORECASE)
    tag = re.sub(r"\s+on\w+\s*=\s*\S+", "", tag, flags=re.IGNORECASE)

    # Remove javascript: URLs
    tag = re.sub(r"href\s*=\s*['\"]?javascript:[^'\">\s]*['\"]?", "", tag, flags=re.IGNORECASE)

    return tag
