"""Abstract repository interface for FeatureFlag aggregate.

Defines the contract for feature flag persistence operations.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from metastore_service.domain.entities.feature_flag import FeatureFlag, TargetingRule
from metastore_service.domain.value_objects import Environment, FeatureName, TenantId


class IFeatureFlagRepository(ABC):
    """Abstract repository interface for FeatureFlag persistence.

    All implementations must support async operations for scalability.
    """

    @abstractmethod
    async def get_by_id(self, flag_id: UUID) -> FeatureFlag | None:
        """Get a feature flag by ID.

        Args:
            flag_id: The unique identifier

        Returns:
            The feature flag if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_name(self, name: FeatureName | str) -> FeatureFlag | None:
        """Get a feature flag by name.

        Args:
            name: The feature flag name

        Returns:
            The feature flag if found, None otherwise
        """
        ...

    @abstractmethod
    async def list_all(
        self,
        enabled_only: bool = False,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeatureFlag]:
        """List all feature flags.

        Args:
            enabled_only: Only return enabled flags
            tags: Optional tag filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of feature flags
        """
        ...

    @abstractmethod
    async def list_active(self) -> list[FeatureFlag]:
        """List all active (enabled and not expired) feature flags.

        Returns:
            List of active feature flags
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeatureFlag]:
        """Search feature flags by name or description.

        Args:
            query: Search query
            enabled_only: Only return enabled flags
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching feature flags
        """
        ...

    @abstractmethod
    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag.

        Args:
            flag: The feature flag to create

        Returns:
            The created feature flag

        Raises:
            DuplicateNameError: If name already exists
        """
        ...

    @abstractmethod
    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        """Update an existing feature flag.

        Args:
            flag: The feature flag to update

        Returns:
            The updated feature flag

        Raises:
            NotFoundError: If the flag doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, flag_id: UUID) -> bool:
        """Delete a feature flag by ID.

        Args:
            flag_id: The unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def evaluate(
        self,
        name: FeatureName | str,
        context: dict[str, Any] | None = None,
        tenant_id: TenantId | str | None = None,
        environment: Environment | None = None,
    ) -> Any:
        """Evaluate a feature flag for the given context.

        This is a convenience method that gets the flag and evaluates it.

        Args:
            name: The feature flag name
            context: Optional context for targeting
            tenant_id: Optional tenant ID
            environment: Optional environment

        Returns:
            The evaluated flag value (bool, str, int, or dict)

        Raises:
            NotFoundError: If the flag doesn't exist
        """
        ...

    @abstractmethod
    async def bulk_evaluate(
        self,
        names: list[str],
        context: dict[str, Any] | None = None,
        tenant_id: TenantId | str | None = None,
        environment: Environment | None = None,
    ) -> dict[str, Any]:
        """Evaluate multiple feature flags at once.

        Args:
            names: List of feature flag names
            context: Optional context for targeting
            tenant_id: Optional tenant ID
            environment: Optional environment

        Returns:
            Dictionary mapping flag name to evaluated value
        """
        ...

    @abstractmethod
    async def exists(self, name: FeatureName | str) -> bool:
        """Check if a feature flag exists.

        Args:
            name: The feature flag name

        Returns:
            True if exists, False otherwise
        """
        ...

    @abstractmethod
    async def count(
        self,
        enabled_only: bool = False,
        tags: list[str] | None = None,
    ) -> int:
        """Count feature flags.

        Args:
            enabled_only: Only count enabled flags
            tags: Optional tag filter

        Returns:
            The count of matching flags
        """
        ...

    @abstractmethod
    async def get_targeting_rules(
        self,
        flag_id: UUID,
    ) -> list[TargetingRule]:
        """Get all targeting rules for a feature flag.

        Args:
            flag_id: The feature flag ID

        Returns:
            List of targeting rules (sorted by priority)
        """
        ...

    @abstractmethod
    async def add_targeting_rule(
        self,
        flag_id: UUID,
        rule: TargetingRule,
    ) -> TargetingRule:
        """Add a targeting rule to a feature flag.

        Args:
            flag_id: The feature flag ID
            rule: The rule to add

        Returns:
            The created rule
        """
        ...

    @abstractmethod
    async def remove_targeting_rule(
        self,
        flag_id: UUID,
        rule_id: UUID,
    ) -> bool:
        """Remove a targeting rule from a feature flag.

        Args:
            flag_id: The feature flag ID
            rule_id: The rule ID to remove

        Returns:
            True if removed, False if not found
        """
        ...

    @abstractmethod
    async def enable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Enable a feature flag.

        Args:
            flag_id: The feature flag ID
            updated_by: User making the change

        Returns:
            True if enabled, False if not found
        """
        ...

    @abstractmethod
    async def disable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Disable a feature flag.

        Args:
            flag_id: The feature flag ID
            updated_by: User making the change

        Returns:
            True if disabled, False if not found
        """
        ...

    @abstractmethod
    async def set_rollout_percentage(
        self,
        flag_id: UUID,
        percentage: int,
        updated_by: str | None = None,
    ) -> bool:
        """Set the rollout percentage for a feature flag.

        Args:
            flag_id: The feature flag ID
            percentage: The new percentage (0-100)
            updated_by: User making the change

        Returns:
            True if updated, False if not found
        """
        ...
