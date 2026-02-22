"""Feature flag evaluation service with percentage rollout support.

:class:`FeatureFlagService` wraps a :class:`FeatureFlagProvider` and
adds evaluation logic including:
- Boolean enabled check
- Percentage-based rollout (deterministic hashing on user ID)
- Explicit allow/deny lists
- Default-false for missing flags
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from shared.feature_flags.base import FeatureFlag, FeatureFlagProvider

logger = logging.getLogger(__name__)


class FeatureFlagService:
    """High-level feature flag evaluation API.

    Attributes:
        provider: The underlying flag storage backend.
        overrides: Local overrides that take precedence over provider flags.
            Useful for tests or environment-specific force-enables.

    Example:
        >>> svc = FeatureFlagService(provider=my_provider)
        >>> if await svc.is_enabled("new-checkout", user_id="usr-42"):
        ...     show_new_checkout()
    """

    def __init__(
        self,
        *,
        provider: FeatureFlagProvider,
        overrides: dict[str, bool] | None = None,
    ) -> None:
        self.provider = provider
        self.overrides: dict[str, bool] = overrides or {}

    async def is_enabled(
        self,
        name: str,
        *,
        user_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        """Evaluate whether a feature flag is enabled.

        Evaluation order:
        1. Local overrides (highest priority)
        2. Deny list (explicit block)
        3. Allow list (explicit enable)
        4. Percentage rollout (deterministic hash)
        5. Global enabled flag
        6. Default value

        Args:
            name: Flag name.
            user_id: Optional user identifier for percentage rollout.
            attributes: Extra context (unused by base implementation,
                available for custom providers).
            default: Returned when the flag does not exist.

        Returns:
            ``True`` if the feature is enabled for this context.
        """
        # 1. Local override
        if name in self.overrides:
            return self.overrides[name]

        flag = await self.provider.get(name)
        if flag is None:
            return default

        if not flag.enabled:
            return False

        # 2. Deny list
        if user_id and user_id in flag.denied_users:
            return False

        # 3. Allow list
        if user_id and user_id in flag.allowed_users:
            return True

        # 4. Percentage rollout
        if flag.rollout_percentage < 100.0:
            if user_id is None:
                # Without a user ID we can't do deterministic rollout
                return default
            return self._in_rollout(name, user_id, flag.rollout_percentage)

        # 5. Globally enabled
        return True

    async def get_flag(self, name: str) -> FeatureFlag | None:
        """Retrieve the raw flag definition."""
        return await self.provider.get(name)

    async def get_all_flags(self) -> list[FeatureFlag]:
        """Retrieve all flag definitions."""
        return await self.provider.get_all()

    async def set_flag(self, flag: FeatureFlag) -> None:
        """Create or update a flag."""
        await self.provider.save(flag)

    async def delete_flag(self, name: str) -> None:
        """Delete a flag."""
        await self.provider.delete(name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _in_rollout(flag_name: str, user_id: str, percentage: float) -> bool:
        """Deterministic hash-based rollout check.

        Produces a consistent yes/no for a given ``(flag, user)`` pair
        so the same user always sees the same result.
        """
        digest = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percentage


async def feature_enabled(
    provider: FeatureFlagProvider,
    name: str,
    *,
    user_id: str | None = None,
    default: bool = False,
) -> bool:
    """Convenience function for one-off flag checks.

    Wraps :class:`FeatureFlagService` for simple call-sites where
    you don't want to instantiate the full service.

    Args:
        provider: Flag storage backend.
        name: Flag name.
        user_id: Optional user ID for rollout.
        default: Returned when the flag does not exist.

    Returns:
        ``True`` if enabled.
    """
    svc = FeatureFlagService(provider=provider)
    return await svc.is_enabled(name, user_id=user_id, default=default)
