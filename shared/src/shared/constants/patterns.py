"""
Common regex patterns for validation.

This module provides pre-compiled regex patterns for common validation
scenarios like email, UUID, URL, and other string formats.

Example:
    >>> from shared.constants import Patterns
    >>> if Patterns.is_valid_email("user@example.com"):
    ...     print("Valid email!")
"""

from __future__ import annotations

import re
from re import Pattern

__all__ = ["Patterns"]


class Patterns:
    """
    Collection of pre-compiled regex patterns for common validations.

    All patterns are compiled at module load time for optimal performance.

    Example:
        >>> Patterns.EMAIL.match("user@example.com")
        <re.Match object; ...>
        >>> Patterns.is_valid_email("invalid")
        False
    """

    # Email pattern - RFC 5322 simplified
    EMAIL: Pattern[str] = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # UUID pattern - supports versions 1-5
    UUID: Pattern[str] = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    # URL pattern - HTTP/HTTPS
    URL: Pattern[str] = re.compile(
        r"^https?://[^\s/$.?#].[^\s]*$",
        re.IGNORECASE,
    )

    # URL slug pattern - lowercase letters, numbers, hyphens
    SLUG: Pattern[str] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    # Phone number pattern - international format
    PHONE: Pattern[str] = re.compile(
        r"^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}$"
    )

    # Username pattern - alphanumeric with underscores and hyphens
    USERNAME: Pattern[str] = re.compile(r"^[a-zA-Z0-9_-]+$")

    # Semantic version pattern
    SEMVER: Pattern[str] = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    # IPv4 address pattern
    IPV4: Pattern[str] = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )

    # ISO 8601 datetime pattern (basic)
    ISO_DATETIME: Pattern[str] = re.compile(
        r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
    )

    # JWT token pattern (basic structure check)
    JWT: Pattern[str] = re.compile(
        r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$"
    )

    # Hex color pattern
    HEX_COLOR: Pattern[str] = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

    # For extraction (findall) - patterns without anchors
    _EMAIL_EXTRACT: Pattern[str] = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    _UUID_EXTRACT: Pattern[str] = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    @classmethod
    def is_valid_email(cls, value: str) -> bool:
        """
        Check if a string is a valid email address.

        Args:
            value: The string to validate.

        Returns:
            True if valid email format.

        Example:
            >>> Patterns.is_valid_email("user@example.com")
            True
        """
        return cls.EMAIL.match(value) is not None

    @classmethod
    def is_valid_uuid(cls, value: str) -> bool:
        """
        Check if a string is a valid UUID.

        Args:
            value: The string to validate.

        Returns:
            True if valid UUID format.

        Example:
            >>> Patterns.is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
            True
        """
        return cls.UUID.match(value) is not None

    @classmethod
    def is_valid_url(cls, value: str) -> bool:
        """
        Check if a string is a valid HTTP/HTTPS URL.

        Args:
            value: The string to validate.

        Returns:
            True if valid URL format.
        """
        return cls.URL.match(value) is not None

    @classmethod
    def is_valid_slug(cls, value: str) -> bool:
        """
        Check if a string is a valid URL slug.

        Args:
            value: The string to validate.

        Returns:
            True if valid slug format.
        """
        return cls.SLUG.match(value) is not None

    @classmethod
    def is_valid_phone(cls, value: str) -> bool:
        """
        Check if a string is a valid phone number.

        Args:
            value: The string to validate.

        Returns:
            True if valid phone format.
        """
        return cls.PHONE.match(value) is not None

    @classmethod
    def is_valid_username(cls, value: str) -> bool:
        """
        Check if a string is a valid username.

        Args:
            value: The string to validate.

        Returns:
            True if valid username format.
        """
        return cls.USERNAME.match(value) is not None

    @classmethod
    def is_valid_semver(cls, value: str) -> bool:
        """
        Check if a string is a valid semantic version.

        Args:
            value: The string to validate.

        Returns:
            True if valid semver format.
        """
        return cls.SEMVER.match(value) is not None

    @classmethod
    def is_valid_ipv4(cls, value: str) -> bool:
        """
        Check if a string is a valid IPv4 address.

        Args:
            value: The string to validate.

        Returns:
            True if valid IPv4 format.
        """
        return cls.IPV4.match(value) is not None

    @classmethod
    def is_valid_jwt(cls, value: str) -> bool:
        """
        Check if a string has valid JWT structure.

        Note: This only validates the structure, not the signature.

        Args:
            value: The string to validate.

        Returns:
            True if valid JWT structure.
        """
        return cls.JWT.match(value) is not None

    @classmethod
    def extract_emails(cls, text: str) -> list[str]:
        """
        Extract all email addresses from text.

        Args:
            text: The text to search.

        Returns:
            List of email addresses found.

        Example:
            >>> Patterns.extract_emails("Contact us at info@example.com")
            ['info@example.com']
        """
        return cls._EMAIL_EXTRACT.findall(text)

    @classmethod
    def extract_uuids(cls, text: str) -> list[str]:
        """
        Extract all UUIDs from text.

        Args:
            text: The text to search.

        Returns:
            List of UUIDs found.

        Example:
            >>> Patterns.extract_uuids("ID: 123e4567-e89b-12d3-a456-426614174000")
            ['123e4567-e89b-12d3-a456-426614174000']
        """
        return cls._UUID_EXTRACT.findall(text)
