"""
JSON serialization utilities with support for complex types.

This module provides enhanced JSON serialization capabilities including
support for datetime, UUID, Decimal, Enum, dataclasses, and Pydantic models.

Example:
    >>> from shared.utils.serialization import serialize_json
    >>> from datetime import datetime
    >>> data = {"timestamp": datetime.now(), "value": Decimal("99.99")}
    >>> serialize_json(data)
    '{"timestamp": "2024-01-15T10:30:45", "value": 99.99}'
"""

from __future__ import annotations

import base64
import dataclasses
import datetime
import json
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    pass

__all__ = [
    "CustomJSONEncoder",
    "serialize_json",
    "deserialize_json",
    "safe_serialize",
]


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles common Python types.

    Supports:
    - datetime, date, time objects (ISO 8601 format)
    - UUID (string representation)
    - Decimal (float conversion)
    - Enum (value extraction)
    - set, frozenset (list conversion)
    - bytes (base64 encoding)
    - Pydantic models (dict conversion)
    - dataclasses (dict conversion)

    Example:
        >>> import json
        >>> from uuid import UUID
        >>> data = {"id": UUID("12345678-1234-5678-1234-567812345678")}
        >>> json.dumps(data, cls=CustomJSONEncoder)
        '{"id": "12345678-1234-5678-1234-567812345678"}'
    """

    def default(self, obj: Any) -> Any:
        """
        Convert object to JSON-serializable type.

        Args:
            obj: Object to convert.

        Returns:
            JSON-serializable representation.

        Raises:
            TypeError: If object type is not supported.
        """
        # datetime types
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, datetime.time):
            return obj.isoformat()

        # UUID
        if isinstance(obj, UUID):
            return str(obj)

        # Decimal
        if isinstance(obj, Decimal):
            return float(obj)

        # Enum
        if isinstance(obj, Enum):
            return obj.value

        # Sets
        if isinstance(obj, (set, frozenset)):
            return list(obj)

        # Bytes
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")

        # Pydantic models (check for model_dump method)
        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        # Legacy Pydantic v1 (check for dict method)
        if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
            return obj.dict()

        # Dataclasses
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)

        # Let the base class raise TypeError for unknown types
        return super().default(obj)


def serialize_json(
    data: Any,
    *,
    pretty: bool = False,
    ensure_ascii: bool = False,
) -> str:
    """
    Serialize data to JSON string with support for complex types.

    Uses CustomJSONEncoder to handle datetime, UUID, Decimal, etc.

    Args:
        data: Data to serialize.
        pretty: Whether to format with indentation.
        ensure_ascii: Whether to escape non-ASCII characters.

    Returns:
        JSON string representation.

    Example:
        >>> serialize_json({"name": "test", "value": 42})
        '{"name": "test", "value": 42}'
    """
    kwargs: dict[str, Any] = {
        "cls": CustomJSONEncoder,
        "ensure_ascii": ensure_ascii,
    }

    if pretty:
        kwargs["indent"] = 2
        kwargs["sort_keys"] = True

    return json.dumps(data, **kwargs)


def deserialize_json(json_str: str) -> Any:
    """
    Deserialize JSON string to Python object.

    Args:
        json_str: JSON string to parse.

    Returns:
        Parsed Python object.

    Raises:
        ValueError: If JSON is invalid.

    Example:
        >>> deserialize_json('{"name": "test"}')
        {'name': 'test'}
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def safe_serialize(
    data: Any,
    *,
    fallback: str | None = None,
) -> str:
    """
    Safely serialize data to JSON, returning fallback on failure.

    This is useful for logging or debugging where serialization should
    never raise an exception.

    Args:
        data: Data to serialize.
        fallback: String to return if serialization fails.
                  If None, returns a representation of the error.

    Returns:
        JSON string or fallback string.

    Example:
        >>> safe_serialize({"name": "test"})
        '{"name": "test"}'
        >>> safe_serialize(lambda x: x)  # Unserializable
        '<Unserializable: function>'
    """
    try:
        return serialize_json(data)
    except (TypeError, ValueError, OverflowError, RecursionError) as e:
        if fallback is not None:
            return fallback
        
        # Try to provide a useful representation
        type_name = type(data).__name__
        return f"<Unserializable: {type_name}>"
