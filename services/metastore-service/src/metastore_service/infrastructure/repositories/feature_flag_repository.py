"""PostgreSQL repository implementation for FeatureFlag aggregate."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from metastore_service.domain.entities.feature_flag import FeatureFlag, TargetingRule
from metastore_service.domain.repositories.feature_flag_repository import IFeatureFlagRepository
from metastore_service.domain.value_objects import (
    Environment,
    FeatureName,
    Operator,
    Percentage,
    TenantId,
)
from metastore_service.infrastructure.database.models import (
    FeatureFlagModel,
    TargetingRuleModel,
)

logger = logging.getLogger(__name__)


class PostgresFeatureFlagRepository(IFeatureFlagRepository):
    """PostgreSQL implementation of the feature flag repository."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    def _to_domain(self, model: FeatureFlagModel) -> FeatureFlag:
        """Convert database model to domain entity."""
        rules = [
            TargetingRule(
                id=r.id,
                feature_flag_id=r.feature_flag_id,
                priority=r.priority,
                attribute=r.attribute,
                operator=r.operator,
                value=r.value,
                result=r.result,
                description=r.description,
            )
            for r in (model.targeting_rules or [])
        ]

        # Convert environment overrides from string keys to enum
        env_overrides = {}
        for env_str, value in (model.environment_overrides or {}).items():
            try:
                env = Environment(env_str)
                env_overrides[env] = value
            except ValueError:
                pass  # Skip invalid environments

        return FeatureFlag(
            id=model.id,
            name=FeatureName(model.name),
            description=model.description,
            enabled=model.enabled,
            default_value=model.default_value,
            rollout_percentage=Percentage(model.rollout_percentage),
            targeting_rules=rules,
            tenant_overrides=model.tenant_overrides or {},
            environment_overrides=env_overrides,
            expires_at=model.expires_at,
            tags=model.tags or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
        )

    def _to_model(self, entity: FeatureFlag) -> FeatureFlagModel:
        """Convert domain entity to database model."""
        # Convert environment overrides to string keys
        env_overrides = {env.value: value for env, value in entity.environment_overrides.items()}

        return FeatureFlagModel(
            id=entity.id,
            name=entity.name.value,
            description=entity.description,
            enabled=entity.enabled,
            default_value=entity.default_value,
            rollout_percentage=entity.rollout_percentage.value,
            tenant_overrides=entity.tenant_overrides,
            environment_overrides=env_overrides,
            expires_at=entity.expires_at,
            tags=entity.tags,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    async def get_by_id(self, flag_id: UUID) -> FeatureFlag | None:
        """Get a feature flag by ID."""
        query = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
            .where(FeatureFlagModel.id == flag_id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def get_by_name(self, name: FeatureName | str) -> FeatureFlag | None:
        """Get a feature flag by name."""
        name_str = name.value if isinstance(name, FeatureName) else name

        query = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
            .where(FeatureFlagModel.name == name_str)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def list_all(
        self,
        enabled_only: bool = False,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeatureFlag]:
        """List all feature flags."""
        conditions = []

        if enabled_only:
            conditions.append(FeatureFlagModel.enabled == True)

        if tags:
            conditions.append(FeatureFlagModel.tags.overlap(tags))

        query = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
        )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(FeatureFlagModel.name).limit(limit).offset(offset)

        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def list_active(self) -> list[FeatureFlag]:
        """List all active (enabled and not expired) feature flags."""
        now = datetime.now(timezone.utc)

        query = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
            .where(
                and_(
                    FeatureFlagModel.enabled == True,
                    or_(
                        FeatureFlagModel.expires_at.is_(None),
                        FeatureFlagModel.expires_at > now,
                    ),
                )
            )
            .order_by(FeatureFlagModel.name)
        )

        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def search(
        self,
        query: str,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeatureFlag]:
        """Search feature flags by name or description."""
        pattern = query.replace("*", "%").replace("?", "_")

        conditions = [
            or_(
                FeatureFlagModel.name.ilike(f"%{pattern}%"),
                FeatureFlagModel.description.ilike(f"%{pattern}%"),
            )
        ]

        if enabled_only:
            conditions.append(FeatureFlagModel.enabled == True)

        stmt = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
            .where(and_(*conditions))
            .order_by(FeatureFlagModel.name)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        model = self._to_model(flag)

        # Add targeting rules
        for r in flag.targeting_rules:
            rule_model = TargetingRuleModel(
                id=r.id,
                feature_flag_id=flag.id,
                priority=r.priority,
                attribute=r.attribute,
                operator=r.operator,
                value=r.value,
                result=r.result,
                description=r.description,
            )
            model.targeting_rules.append(rule_model)

        self._session.add(model)
        await self._session.flush()

        logger.debug(f"Created feature flag: {flag.id}")
        return flag

    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        """Update an existing feature flag."""
        # Get existing model
        query = (
            select(FeatureFlagModel)
            .options(selectinload(FeatureFlagModel.targeting_rules))
            .where(FeatureFlagModel.id == flag.id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError(f"Feature flag {flag.id} not found")

        # Update model attributes
        env_overrides = {env.value: value for env, value in flag.environment_overrides.items()}

        model.name = flag.name.value
        model.description = flag.description
        model.enabled = flag.enabled
        model.default_value = flag.default_value
        model.rollout_percentage = flag.rollout_percentage.value
        model.tenant_overrides = flag.tenant_overrides
        model.environment_overrides = env_overrides
        model.expires_at = flag.expires_at
        model.tags = flag.tags
        model.updated_at = flag.updated_at
        model.updated_by = flag.updated_by

        # Sync targeting rules
        existing_rule_ids = {r.id for r in model.targeting_rules}
        new_rule_ids = {r.id for r in flag.targeting_rules}

        # Remove deleted rules
        for rule in list(model.targeting_rules):
            if rule.id not in new_rule_ids:
                model.targeting_rules.remove(rule)

        # Add or update rules
        for r in flag.targeting_rules:
            if r.id not in existing_rule_ids:
                rule_model = TargetingRuleModel(
                    id=r.id,
                    feature_flag_id=flag.id,
                    priority=r.priority,
                    attribute=r.attribute,
                    operator=r.operator,
                    value=r.value,
                    result=r.result,
                    description=r.description,
                )
                model.targeting_rules.append(rule_model)
            else:
                # Update existing rule
                for rule in model.targeting_rules:
                    if rule.id == r.id:
                        rule.priority = r.priority
                        rule.attribute = r.attribute
                        rule.operator = r.operator
                        rule.value = r.value
                        rule.result = r.result
                        rule.description = r.description
                        break

        await self._session.flush()

        logger.debug(f"Updated feature flag: {flag.id}")
        return flag

    async def delete(self, flag_id: UUID) -> bool:
        """Delete a feature flag by ID."""
        stmt = delete(FeatureFlagModel).where(FeatureFlagModel.id == flag_id)
        result = await self._session.execute(stmt)
        await self._session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted feature flag: {flag_id}")
        return deleted

    async def evaluate(
        self,
        name: FeatureName | str,
        context: dict[str, Any] | None = None,
        tenant_id: TenantId | str | None = None,
        environment: Environment | None = None,
    ) -> Any:
        """Evaluate a feature flag for the given context."""
        flag = await self.get_by_name(name)
        if flag is None:
            raise ValueError(f"Feature flag '{name}' not found")

        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
        return flag.evaluate(context, tenant_str, environment)

    async def bulk_evaluate(
        self,
        names: list[str],
        context: dict[str, Any] | None = None,
        tenant_id: TenantId | str | None = None,
        environment: Environment | None = None,
    ) -> dict[str, Any]:
        """Evaluate multiple feature flags at once."""
        results = {}

        for name in names:
            try:
                value = await self.evaluate(name, context, tenant_id, environment)
                results[name] = value
            except ValueError:
                results[name] = None

        return results

    async def exists(self, name: FeatureName | str) -> bool:
        """Check if a feature flag exists."""
        name_str = name.value if isinstance(name, FeatureName) else name

        query = select(func.count(FeatureFlagModel.id)).where(
            FeatureFlagModel.name == name_str
        )
        result = await self._session.execute(query)
        count = result.scalar_one()

        return count > 0

    async def count(
        self,
        enabled_only: bool = False,
        tags: list[str] | None = None,
    ) -> int:
        """Count feature flags."""
        conditions = []

        if enabled_only:
            conditions.append(FeatureFlagModel.enabled == True)

        if tags:
            conditions.append(FeatureFlagModel.tags.overlap(tags))

        query = select(func.count(FeatureFlagModel.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_targeting_rules(
        self,
        flag_id: UUID,
    ) -> list[TargetingRule]:
        """Get all targeting rules for a feature flag."""
        query = (
            select(TargetingRuleModel)
            .where(TargetingRuleModel.feature_flag_id == flag_id)
            .order_by(TargetingRuleModel.priority)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [
            TargetingRule(
                id=m.id,
                feature_flag_id=m.feature_flag_id,
                priority=m.priority,
                attribute=m.attribute,
                operator=m.operator,
                value=m.value,
                result=m.result,
                description=m.description,
            )
            for m in models
        ]

    async def add_targeting_rule(
        self,
        flag_id: UUID,
        rule: TargetingRule,
    ) -> TargetingRule:
        """Add a targeting rule to a feature flag."""
        rule_model = TargetingRuleModel(
            id=rule.id,
            feature_flag_id=flag_id,
            priority=rule.priority,
            attribute=rule.attribute,
            operator=rule.operator,
            value=rule.value,
            result=rule.result,
            description=rule.description,
        )

        self._session.add(rule_model)
        await self._session.flush()

        return rule

    async def remove_targeting_rule(
        self,
        flag_id: UUID,
        rule_id: UUID,
    ) -> bool:
        """Remove a targeting rule from a feature flag."""
        stmt = delete(TargetingRuleModel).where(
            and_(
                TargetingRuleModel.feature_flag_id == flag_id,
                TargetingRuleModel.id == rule_id,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0

    async def enable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Enable a feature flag."""
        stmt = (
            update(FeatureFlagModel)
            .where(FeatureFlagModel.id == flag_id)
            .values(
                enabled=True,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0

    async def disable(
        self,
        flag_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Disable a feature flag."""
        stmt = (
            update(FeatureFlagModel)
            .where(FeatureFlagModel.id == flag_id)
            .values(
                enabled=False,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0

    async def set_rollout_percentage(
        self,
        flag_id: UUID,
        percentage: int,
        updated_by: str | None = None,
    ) -> bool:
        """Set the rollout percentage for a feature flag."""
        stmt = (
            update(FeatureFlagModel)
            .where(FeatureFlagModel.id == flag_id)
            .values(
                rollout_percentage=percentage,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0
