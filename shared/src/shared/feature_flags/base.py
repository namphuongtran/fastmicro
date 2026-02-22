"""Core feature flag types and in-memory provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class FeatureFlag:
    """A single feature flag definition.

    Attributes:
        name: Unique flag identifier (kebab-case recommended).
        enabled: Global on/off switch.
        description: Human-readable explanation of what the flag controls.
        rollout_percentage: Percentage of users/requests that see the feature
            (0–100).  Only evaluated when ``enabled=True``.
        allowed_users: Explicit user IDs that always get the feature.
        denied_users: Explicit user IDs that never get the feature.
        metadata: Arbitrary key-value data (owner, ticket, etc.).
        created_at: When the flag was created.
        updated_at: When the flag was last modified.
    """

    name: str
    enabled: bool = False
    description: str = ""
    rollout_percentage: float = 100.0
    allowed_users: set[str] = field(default_factory=set)
    denied_users: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class FeatureFlagProvider(Protocol):
    """Protocol for feature flag storage backends.

    Implementations may use an in-memory dict, database,
    external service (LaunchDarkly, Unleash, Flagsmith), etc.
    """

    async def get(self, name: str) -> FeatureFlag | None:
        """Retrieve a flag by name."""
        ...

    async def get_all(self) -> list[FeatureFlag]:
        """Return all defined flags."""
        ...

    async def save(self, flag: FeatureFlag) -> None:
        """Create or update a flag."""
        ...

    async def delete(self, name: str) -> None:
        """Remove a flag."""
        ...


class InMemoryFlagProvider:
    """In-memory feature flag provider for tests and local development.

    Example:
        >>> provider = InMemoryFlagProvider()
        >>> provider.set("beta-ui", FeatureFlag(name="beta-ui", enabled=True))
        >>> flag = await provider.get("beta-ui")
        >>> assert flag is not None and flag.enabled
    """

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag] = {}

    def set(self, name: str, flag: FeatureFlag) -> None:
        """Synchronously set a flag (convenience for test setup)."""
        self._flags[name] = flag

    async def get(self, name: str) -> FeatureFlag | None:
        return self._flags.get(name)

    async def get_all(self) -> list[FeatureFlag]:
        return list(self._flags.values())

    async def save(self, flag: FeatureFlag) -> None:
        self._flags[flag.name] = flag

    async def delete(self, name: str) -> None:
        self._flags.pop(name, None)

    def clear(self) -> None:
        self._flags.clear()
