"""Feature Flag application service.

Orchestrates feature flag operations using domain entities and repository interfaces.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

from metastore_service.application.dtos.feature_flag_dtos import (
    CreateFeatureFlagDTO,
    EvaluateFeatureFlagDTO,
    FeatureFlagDTO,
    FeatureFlagListDTO,
    TargetingRuleDTO,
    UpdateFeatureFlagDTO,
)
from metastore_service.domain.entities.feature_flag import FeatureFlag
from metastore_service.domain.repositories.feature_flag_repository import IFeatureFlagRepository
from metastore_service.domain.value_objects import Environment

logger = logging.getLogger(__name__)


class ICacheService(Protocol):
    """Cache service interface for feature flag caching."""

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_pattern(self, pattern: str) -> None: ...


class FeatureFlagService:
    """Application service for feature flag operations.

    Handles business logic, evaluation caching, and orchestration between
    the domain layer and infrastructure concerns.
    """

    def __init__(
        self,
        repository: IFeatureFlagRepository,
        cache: ICacheService | None = None,
        cache_ttl: int = 60,  # 1 minute default for flags
    ):
        """Initialize the feature flag service.

        Args:
            repository: Feature flag repository implementation
            cache: Optional cache service for hot data
            cache_ttl: Cache TTL in seconds
        """
        self._repository = repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    def _cache_key(self, name: str) -> str:
        """Generate a cache key for a flag."""
        return f"feature_flag:{name}"

    async def create(
        self,
        dto: CreateFeatureFlagDTO,
        created_by: str | None = None,
    ) -> FeatureFlagDTO:
        """Create a new feature flag.

        Args:
            dto: Creation data
            created_by: User creating the flag

        Returns:
            The created feature flag

        Raises:
            ValueError: If name already exists
        """
        # Check for duplicates
        existing = await self._repository.exists(dto.name)
        if existing:
            raise ValueError(f"Feature flag '{dto.name}' already exists")

        # Create domain entity
        flag = FeatureFlag.create(
            name=dto.name,
            description=dto.description,
            enabled=dto.enabled,
            default_value=dto.default_value,
            rollout_percentage=dto.rollout_percentage,
            expires_at=dto.expires_at,
            tags=dto.tags,
            created_by=created_by,
        )

        # Add targeting rules
        for rule_dto in dto.targeting_rules:
            flag.add_targeting_rule(
                attribute=rule_dto.attribute,
                operator=rule_dto.operator,
                value=rule_dto.value,
                result=rule_dto.result,
                priority=rule_dto.priority,
                description=rule_dto.description,
            )

        # Persist
        created = await self._repository.create(flag)

        logger.info(
            "Created feature flag",
            extra={
                "flag_id": str(created.id),
                "name": dto.name,
                "enabled": dto.enabled,
                "created_by": created_by,
            },
        )

        return FeatureFlagDTO.from_entity(created)

    async def get_by_id(self, flag_id: UUID) -> FeatureFlagDTO | None:
        """Get a feature flag by ID.

        Args:
            flag_id: The flag ID

        Returns:
            The feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None
        return FeatureFlagDTO.from_entity(flag)

    async def get_by_name(self, name: str) -> FeatureFlagDTO | None:
        """Get a feature flag by name.

        Args:
            name: The flag name

        Returns:
            The feature flag or None if not found
        """
        # Try cache first
        if self._cache:
            cache_key = self._cache_key(name)
            cached = await self._cache.get(cache_key)
            if cached:
                return FeatureFlagDTO(**cached)

        # Get from repository
        flag = await self._repository.get_by_name(name)
        if flag is None:
            return None

        dto = FeatureFlagDTO.from_entity(flag)

        # Cache result
        if self._cache:
            cache_key = self._cache_key(name)
            await self._cache.set(cache_key, dto.model_dump(mode="json"), self._cache_ttl)

        return dto

    async def evaluate(
        self,
        name: str,
        evaluation: EvaluateFeatureFlagDTO | None = None,
    ) -> Any:
        """Evaluate a feature flag.

        Args:
            name: The flag name
            evaluation: Optional evaluation context

        Returns:
            The evaluated flag value

        Raises:
            ValueError: If flag not found
        """
        flag = await self._repository.get_by_name(name)
        if flag is None:
            raise ValueError(f"Feature flag '{name}' not found")

        context = evaluation.context if evaluation else None
        tenant_id = evaluation.tenant_id if evaluation else None
        environment = evaluation.environment if evaluation else None

        result = flag.evaluate(
            context=context,
            tenant_id=tenant_id,
            environment=environment,
        )

        logger.debug(
            "Evaluated feature flag",
            extra={
                "flag_name": name,
                "result": result,
                "has_context": context is not None,
            },
        )

        return result

    async def bulk_evaluate(
        self,
        names: list[str],
        context: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        environment: Environment | None = None,
    ) -> dict[str, Any]:
        """Evaluate multiple feature flags at once.

        Args:
            names: List of flag names
            context: Optional context for targeting
            tenant_id: Optional tenant ID
            environment: Optional environment

        Returns:
            Dictionary mapping flag name to evaluated value
        """
        results = await self._repository.bulk_evaluate(
            names=names,
            context=context,
            tenant_id=tenant_id,
            environment=environment,
        )
        return results

    async def update(
        self,
        flag_id: UUID,
        dto: UpdateFeatureFlagDTO,
        updated_by: str | None = None,
    ) -> FeatureFlagDTO | None:
        """Update a feature flag.

        Args:
            flag_id: The flag ID
            dto: Update data
            updated_by: User making the update

        Returns:
            The updated feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None

        # Apply updates
        if dto.description is not None:
            flag.description = dto.description

        if dto.enabled is not None:
            if dto.enabled:
                flag.enable(updated_by)
            else:
                flag.disable(updated_by)

        if dto.default_value is not None:
            flag.default_value = dto.default_value

        if dto.rollout_percentage is not None:
            flag.set_rollout_percentage(dto.rollout_percentage, updated_by)

        if dto.expires_at is not None:
            flag.expires_at = dto.expires_at

        if dto.tags is not None:
            flag.tags = dto.tags

        # Persist
        updated = await self._repository.update(flag)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        logger.info(
            "Updated feature flag",
            extra={
                "flag_id": str(flag_id),
                "name": flag.name.value,
                "updated_by": updated_by,
            },
        )

        return FeatureFlagDTO.from_entity(updated)

    async def delete(self, flag_id: UUID) -> bool:
        """Delete a feature flag.

        Args:
            flag_id: The flag ID

        Returns:
            True if deleted, False if not found
        """
        # Get flag first for cache invalidation
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return False

        # Delete
        result = await self._repository.delete(flag_id)

        # Invalidate cache
        if self._cache and result:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        logger.info(
            "Deleted feature flag",
            extra={"flag_id": str(flag_id), "name": flag.name.value},
        )

        return result

    async def list_all(
        self,
        enabled_only: bool = False,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FeatureFlagListDTO:
        """List all feature flags.

        Args:
            enabled_only: Only return enabled flags
            tags: Optional tag filter
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of feature flags
        """
        flags = await self._repository.list_all(
            enabled_only=enabled_only,
            tags=tags,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(enabled_only=enabled_only, tags=tags)

        return FeatureFlagListDTO.from_entities(flags, total, limit, offset)

    async def search(
        self,
        query: str,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> FeatureFlagListDTO:
        """Search feature flags.

        Args:
            query: Search query
            enabled_only: Only return enabled flags
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of matching flags
        """
        flags = await self._repository.search(
            query=query,
            enabled_only=enabled_only,
            limit=limit,
            offset=offset,
        )
        total = len(flags) if len(flags) < limit else limit + offset + 1

        return FeatureFlagListDTO.from_entities(flags, total, limit, offset)

    async def enable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Enable a feature flag.

        Args:
            flag_id: The flag ID
            updated_by: User making the change

        Returns:
            True if enabled, False if not found
        """
        result = await self._repository.enable(flag_id, updated_by)

        if result:
            # Invalidate cache
            flag = await self._repository.get_by_id(flag_id)
            if flag and self._cache:
                cache_key = self._cache_key(flag.name.value)
                await self._cache.delete(cache_key)

            logger.info(
                "Enabled feature flag",
                extra={"flag_id": str(flag_id), "updated_by": updated_by},
            )

        return result

    async def disable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Disable a feature flag.

        Args:
            flag_id: The flag ID
            updated_by: User making the change

        Returns:
            True if disabled, False if not found
        """
        result = await self._repository.disable(flag_id, updated_by)

        if result:
            # Invalidate cache
            flag = await self._repository.get_by_id(flag_id)
            if flag and self._cache:
                cache_key = self._cache_key(flag.name.value)
                await self._cache.delete(cache_key)

            logger.info(
                "Disabled feature flag",
                extra={"flag_id": str(flag_id), "updated_by": updated_by},
            )

        return result

    async def add_targeting_rule(
        self,
        flag_id: UUID,
        rule_dto: TargetingRuleDTO,
    ) -> FeatureFlagDTO | None:
        """Add a targeting rule to a feature flag.

        Args:
            flag_id: The flag ID
            rule_dto: The rule to add

        Returns:
            The updated feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None

        flag.add_targeting_rule(
            attribute=rule_dto.attribute,
            operator=rule_dto.operator,
            value=rule_dto.value,
            result=rule_dto.result,
            priority=rule_dto.priority,
            description=rule_dto.description,
        )

        updated = await self._repository.update(flag)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        return FeatureFlagDTO.from_entity(updated)

    async def remove_targeting_rule(
        self,
        flag_id: UUID,
        rule_id: UUID,
    ) -> FeatureFlagDTO | None:
        """Remove a targeting rule from a feature flag.

        Args:
            flag_id: The flag ID
            rule_id: The rule ID to remove

        Returns:
            The updated feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None

        removed = flag.remove_targeting_rule(rule_id)
        if not removed:
            return FeatureFlagDTO.from_entity(flag)

        updated = await self._repository.update(flag)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        return FeatureFlagDTO.from_entity(updated)

    async def set_rollout_percentage(
        self,
        flag_id: UUID,
        percentage: int,
        updated_by: str | None = None,
    ) -> bool:
        """Set the rollout percentage for a feature flag.

        Args:
            flag_id: The flag ID
            percentage: New percentage (0-100)
            updated_by: User making the change

        Returns:
            True if updated, False if not found
        """
        result = await self._repository.set_rollout_percentage(
            flag_id, percentage, updated_by
        )

        if result:
            # Invalidate cache
            flag = await self._repository.get_by_id(flag_id)
            if flag and self._cache:
                cache_key = self._cache_key(flag.name.value)
                await self._cache.delete(cache_key)

            logger.info(
                "Updated rollout percentage",
                extra={
                    "flag_id": str(flag_id),
                    "percentage": percentage,
                    "updated_by": updated_by,
                },
            )

        return result

    async def set_tenant_override(
        self,
        flag_id: UUID,
        tenant_id: str,
        value: Any,
    ) -> FeatureFlagDTO | None:
        """Set an override value for a specific tenant.

        Args:
            flag_id: The flag ID
            tenant_id: The tenant identifier
            value: The override value

        Returns:
            The updated feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None

        flag.set_tenant_override(tenant_id, value)
        updated = await self._repository.update(flag)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        return FeatureFlagDTO.from_entity(updated)

    async def set_environment_override(
        self,
        flag_id: UUID,
        environment: Environment,
        value: Any,
    ) -> FeatureFlagDTO | None:
        """Set an override value for a specific environment.

        Args:
            flag_id: The flag ID
            environment: The environment
            value: The override value

        Returns:
            The updated feature flag or None if not found
        """
        flag = await self._repository.get_by_id(flag_id)
        if flag is None:
            return None

        flag.set_environment_override(environment, value)
        updated = await self._repository.update(flag)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(flag.name.value)
            await self._cache.delete(cache_key)

        return FeatureFlagDTO.from_entity(updated)
