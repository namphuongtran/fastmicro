"""Base cache abstractions and serializers.

This module provides the foundational interfaces for the caching system:
- CacheBackend: Protocol for all cache backends
- Serializer: Protocol for value serialization
- Built-in serializers: JsonSerializer, PickleSerializer, NullSerializer

Architecture follows aiocache patterns with two-tier support.
"""

from __future__ import annotations

import json
import pickle
from abc import ABC, abstractmethod
from typing import (
    Any,
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from shared.exceptions import BaseServiceException

# Type variables
V = TypeVar("V")  # Value type
T = TypeVar("T")  # Generic type for serializers


class CacheError(BaseServiceException):
    """Base exception for cache errors."""

    def __init__(
        self,
        message: str = "Cache error occurred",
        *,
        error_code: str = "CACHE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class CacheConnectionError(CacheError):
    """Error connecting to cache backend."""

    def __init__(
        self,
        message: str = "Failed to connect to cache backend",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code="CACHE_CONNECTION_ERROR", details=details)


class CacheSerializationError(CacheError):
    """Error serializing or deserializing cache values."""

    def __init__(
        self,
        message: str = "Serialization error",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code="CACHE_SERIALIZATION_ERROR", details=details)


# ============================================================================
# Serializer Protocol and Implementations
# ============================================================================


class Serializer(Protocol[T]):
    """Protocol for cache value serializers."""

    def serialize(self, value: T) -> bytes:
        """Serialize a value to bytes.

        Args:
            value: Value to serialize.

        Returns:
            Serialized bytes.
        """
        ...

    def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to a value.

        Args:
            data: Bytes to deserialize.

        Returns:
            Deserialized value.
        """
        ...


class NullSerializer:
    """Serializer that does nothing - for in-memory caches.

    Memory caches can store Python objects directly,
    so no serialization is needed.
    """

    def serialize(self, value: Any) -> Any:
        """Return value unchanged."""
        return value

    def deserialize(self, data: Any) -> Any:
        """Return data unchanged."""
        return data


class JsonSerializer:
    """JSON serializer for cache values.

    Best for human-readable, debuggable cache entries.
    Works well with Redis and other string-based backends.

    Example:
        >>> serializer = JsonSerializer()
        >>> data = serializer.serialize({"name": "John", "age": 30})
        >>> serializer.deserialize(data)
        {'name': 'John', 'age': 30}
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        """Initialize JSON serializer.

        Args:
            encoding: String encoding to use.
        """
        self._encoding = encoding

    def serialize(self, value: Any) -> bytes:
        """Serialize value to JSON bytes.

        Args:
            value: Value to serialize (must be JSON-serializable).

        Returns:
            JSON-encoded bytes.

        Raises:
            CacheSerializationError: If serialization fails.
        """
        try:
            return json.dumps(value, default=str).encode(self._encoding)
        except (TypeError, ValueError) as e:
            raise CacheSerializationError(
                f"Failed to serialize value to JSON: {e}",
                details={"value_type": type(value).__name__},
            ) from e

    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to value.

        Args:
            data: JSON-encoded bytes.

        Returns:
            Deserialized Python object.

        Raises:
            CacheSerializationError: If deserialization fails.
        """
        try:
            if isinstance(data, bytes):
                data = data.decode(self._encoding)
            return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise CacheSerializationError(
                f"Failed to deserialize JSON: {e}",
                details={"data_length": len(data) if data else 0},
            ) from e


class PickleSerializer:
    """Pickle serializer for cache values.

    Supports complex Python objects but less portable.
    Use with caution - pickle can execute arbitrary code.

    Example:
        >>> from datetime import datetime
        >>> serializer = PickleSerializer()
        >>> data = serializer.serialize(datetime.now())
        >>> isinstance(serializer.deserialize(data), datetime)
        True
    """

    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL) -> None:
        """Initialize Pickle serializer.

        Args:
            protocol: Pickle protocol version.
        """
        self._protocol = protocol

    def serialize(self, value: Any) -> bytes:
        """Serialize value to pickle bytes.

        Args:
            value: Value to serialize.

        Returns:
            Pickled bytes.

        Raises:
            CacheSerializationError: If serialization fails.
        """
        try:
            return pickle.dumps(value, protocol=self._protocol)
        except (pickle.PicklingError, TypeError) as e:
            raise CacheSerializationError(
                f"Failed to pickle value: {e}",
                details={"value_type": type(value).__name__},
            ) from e

    def deserialize(self, data: bytes) -> Any:
        """Deserialize pickle bytes to value.

        Args:
            data: Pickled bytes.

        Returns:
            Deserialized Python object.

        Raises:
            CacheSerializationError: If deserialization fails.
        """
        try:
            return pickle.loads(data)
        except (pickle.UnpicklingError, TypeError) as e:
            raise CacheSerializationError(
                f"Failed to unpickle value: {e}",
                details={"data_length": len(data) if data else 0},
            ) from e


# ============================================================================
# Cache Backend Protocol
# ============================================================================


@runtime_checkable
class CacheBackend(Protocol[V]):
    """Protocol defining the cache backend interface.

    All cache backends (Memory, Redis, Null) must implement this interface.
    This enables the TieredCacheManager to work with any backend.

    Type Parameters:
        V: The value type stored in the cache.
    """

    @property
    def name(self) -> str:
        """Return the backend name (e.g., 'memory', 'redis', 'null')."""
        ...

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get a value from the cache.

        Args:
            key: Cache key.
            default: Default value if key not found.

        Returns:
            Cached value or default.
        """
        ...

    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (None = use default).

        Returns:
            True if successful.
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if key was deleted, False if not found.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        ...

    async def clear(self, namespace: str | None = None) -> int:
        """Clear cache entries.

        Args:
            namespace: Optional namespace prefix to clear.

        Returns:
            Number of keys cleared.
        """
        ...

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value.

        Args:
            key: Cache key.
            delta: Amount to increment (can be negative).

        Returns:
            New value after increment.
        """
        ...

    async def close(self) -> None:
        """Close the backend connection and release resources."""
        ...


# ============================================================================
# Abstract Base Class for Convenience
# ============================================================================


class AbstractCacheBackend(ABC, Generic[V]):
    """Abstract base class implementing common cache backend functionality.

    Subclasses only need to implement the core operations.
    """

    def __init__(
        self,
        namespace: str = "",
        default_ttl: int | None = None,
        serializer: Serializer[Any] | None = None,
    ) -> None:
        """Initialize cache backend.

        Args:
            namespace: Key namespace prefix.
            default_ttl: Default TTL in seconds.
            serializer: Value serializer.
        """
        self._namespace = namespace
        self._default_ttl = default_ttl
        self._serializer = serializer or NullSerializer()

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""
        ...

    def build_key(self, key: str) -> str:
        """Build full cache key with namespace.

        Args:
            key: Base key.

        Returns:
            Full key with namespace prefix.
        """
        if self._namespace:
            return f"{self._namespace}:{key}"
        return key

    def _get_ttl(self, ttl: int | None) -> int | None:
        """Get effective TTL.

        Args:
            ttl: Explicit TTL or None.

        Returns:
            Effective TTL to use.
        """
        if ttl is not None:
            return ttl
        return self._default_ttl

    @abstractmethod
    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get a value from the cache."""
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in the cache."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    @abstractmethod
    async def clear(self, namespace: str | None = None) -> int:
        """Clear cache entries."""
        ...

    @abstractmethod
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value."""
        ...

    async def close(self) -> None:
        """Close backend (default: no-op)."""
        pass

    async def __aenter__(self) -> AbstractCacheBackend[V]:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
