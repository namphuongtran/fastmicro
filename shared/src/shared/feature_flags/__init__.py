"""Feature flag management for progressive rollouts.

Enables toggling features on/off at runtime without redeployment.
Supports boolean flags, percentage-based rollouts, and user-segment
targeting through a pluggable provider architecture.

Components:
- :class:`FeatureFlag` — flag definition
- :class:`FeatureFlagProvider` — protocol for flag backends
- :class:`InMemoryFlagProvider` — built-in in-memory backend
- :class:`FeatureFlagService` — high-level evaluation API
- :func:`feature_enabled` — simple boolean check helper

Example:
    >>> from shared.feature_flags import (
    ...     FeatureFlag, InMemoryFlagProvider, FeatureFlagService,
    ... )
    >>>
    >>> provider = InMemoryFlagProvider()
    >>> provider.set("dark-mode", FeatureFlag(name="dark-mode", enabled=True))
    >>> svc = FeatureFlagService(provider=provider)
    >>> await svc.is_enabled("dark-mode")
    True
"""

from __future__ import annotations

from shared.feature_flags.base import (
    FeatureFlag,
    FeatureFlagProvider,
    InMemoryFlagProvider,
)
from shared.feature_flags.service import FeatureFlagService, feature_enabled

__all__ = [
    "FeatureFlag",
    "FeatureFlagProvider",
    "InMemoryFlagProvider",
    "FeatureFlagService",
    "feature_enabled",
]
