"""
String manipulation utilities.

This module provides common string operations including slugification,
case conversion, text processing, and sanitization functions.

Example:
    >>> from shared.utils.strings import slugify, truncate
    >>> slugify("Hello World!")
    'hello-world'
    >>> truncate("Hello World", max_length=8)
    'Hello...'
"""

from __future__ import annotations

import re
import secrets
import string
import unicodedata

__all__ = [
    "camel_to_snake",
    "generate_random_string",
    "mask_sensitive",
    "pluralize",
    "sanitize_filename",
    "slugify",
    "snake_to_camel",
    "truncate",
]


def slugify(
    value: str,
    *,
    separator: str = "-",
) -> str:
    """
    Convert a string to URL-friendly slug format.

    Converts to lowercase, removes special characters, and replaces
    spaces/separators with the specified separator.

    Args:
        value: String to slugify.
        separator: Character to use as separator (default: "-").

    Returns:
        URL-friendly slug string.

    Example:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Hello World", separator="_")
        'hello_world'
    """
    if not value:
        return ""

    # Normalize unicode characters
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    value = value.lower()

    # Replace any character that's not alphanumeric with separator
    value = re.sub(r"[^a-z0-9]+", separator, value)

    # Strip leading/trailing separators
    value = value.strip(separator)

    return value


def truncate(
    value: str,
    max_length: int,
    *,
    suffix: str = "...",
) -> str:
    """
    Truncate a string to a maximum length, adding suffix if truncated.

    Args:
        value: String to truncate.
        max_length: Maximum total length (including suffix).
        suffix: Suffix to add when truncated.

    Returns:
        Truncated string.

    Example:
        >>> truncate("Hello World", max_length=8)
        'Hello...'
    """
    if not value or len(value) <= max_length:
        return value

    if max_length <= len(suffix):
        return value[:max_length]

    return value[: max_length - len(suffix)] + suffix


def camel_to_snake(value: str) -> str:
    """
    Convert camelCase or PascalCase to snake_case.

    Args:
        value: String in camelCase or PascalCase.

    Returns:
        String in snake_case.

    Example:
        >>> camel_to_snake("helloWorld")
        'hello_world'
        >>> camel_to_snake("HTTPServer")
        'http_server'
    """
    if not value:
        return ""

    # Insert underscore before uppercase letters
    result = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    result = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", result)

    return result.lower()


def snake_to_camel(
    value: str,
    *,
    pascal: bool = False,
) -> str:
    """
    Convert snake_case to camelCase or PascalCase.

    Args:
        value: String in snake_case.
        pascal: If True, return PascalCase (first letter capitalized).

    Returns:
        String in camelCase or PascalCase.

    Example:
        >>> snake_to_camel("hello_world")
        'helloWorld'
        >>> snake_to_camel("hello_world", pascal=True)
        'HelloWorld'
    """
    if not value:
        return ""

    # Split and capitalize
    parts = value.lower().split("_")

    if pascal:
        return "".join(part.capitalize() for part in parts)
    else:
        return parts[0] + "".join(part.capitalize() for part in parts[1:])


def generate_random_string(
    length: int = 16,
    *,
    include_special: bool = False,
) -> str:
    """
    Generate a cryptographically secure random string.

    Args:
        length: Length of the generated string.
        include_special: Whether to include special characters.

    Returns:
        Random string of specified length.

    Example:
        >>> s = generate_random_string(20)
        >>> len(s)
        20
    """
    alphabet = string.ascii_letters + string.digits

    if include_special:
        alphabet += string.punctuation

    return "".join(secrets.choice(alphabet) for _ in range(length))


def mask_sensitive(
    value: str,
    *,
    visible_chars: int = 4,
    mask_char: str = "*",
) -> str:
    """
    Mask a sensitive string, showing only leading/trailing characters.

    Useful for displaying partial credit cards, API keys, etc.

    Args:
        value: String to mask.
        visible_chars: Number of characters to show at start and end.
        mask_char: Character to use for masking.

    Returns:
        Masked string.

    Example:
        >>> mask_sensitive("1234567890")
        '12****90'
    """
    if not value:
        return ""

    if len(value) <= visible_chars * 2:
        # String too short, just mask the middle
        if len(value) <= 2:
            return mask_char * len(value)
        return value[0] + mask_char * (len(value) - 2) + value[-1]

    start = value[:visible_chars]
    end = value[-visible_chars:]
    middle_length = len(value) - (visible_chars * 2)

    return start + mask_char * middle_length + end


def sanitize_filename(
    filename: str,
    *,
    max_length: int = 255,
    replacement: str = "_",
) -> str:
    """
    Sanitize a string for use as a filename.

    Removes or replaces characters that are invalid in filenames.

    Args:
        filename: Original filename string.
        max_length: Maximum allowed length.
        replacement: Character to replace invalid chars with.

    Returns:
        Sanitized filename.

    Example:
        >>> sanitize_filename("file/name:test")
        'file_name_test'
    """
    if not filename:
        return ""

    # Characters invalid in Windows filenames
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'

    # Replace invalid characters
    result = re.sub(invalid_chars, replacement, filename)

    # Collapse multiple replacements
    result = re.sub(f"{re.escape(replacement)}+", replacement, result)

    # Strip leading/trailing replacement chars and spaces
    result = result.strip(f"{replacement} ")

    # Truncate if necessary
    if len(result) > max_length:
        result = result[:max_length].rstrip(f"{replacement} ")

    return result


def pluralize(
    word: str,
    count: int,
    *,
    plural: str | None = None,
) -> str:
    """
    Return singular or plural form based on count.

    Args:
        word: Singular form of the word.
        count: Number to determine plurality.
        plural: Custom plural form (default: word + "s").

    Returns:
        Singular or plural form.

    Example:
        >>> pluralize("item", 1)
        'item'
        >>> pluralize("item", 2)
        'items'
        >>> pluralize("child", 2, plural="children")
        'children'
    """
    if count == 1:
        return word

    if plural is not None:
        return plural

    return word + "s"
