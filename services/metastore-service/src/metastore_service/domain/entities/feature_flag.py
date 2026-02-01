"""FeatureFlag aggregate - Domain entity for feature flag management.

The FeatureFlag is an aggregate root that manages feature toggles with
targeting rules, rollout percentages, and environment overrides.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from metastore_service.domain.value_objects import (
    Environment,
    FeatureName,
    Operator,
    Percentage,
    TenantId,
)


@dataclass
class TargetingRule:
    """Represents a targeting rule for feature flag evaluation.

    Rules are evaluated in order of priority. First matching rule wins.

    Attributes:
        id: Unique identifier
        priority: Evaluation order (lower = higher priority)
        attribute: The context attribute to check (e.g., 'user.email')
        operator: The comparison operator
        value: The value to compare against
        result: The value to return if rule matches
        description: Human-readable description
    """

    id: UUID
    feature_flag_id: UUID
    priority: int
    attribute: str
    operator: Operator
    value: str
    result: Any  # bool, str, int, or dict
    description: str | None = None

    @classmethod
    def create(
        cls,
        feature_flag_id: UUID,
        priority: int,
        attribute: str,
        operator: Operator,
        value: str,
        result: Any,
        description: str | None = None,
    ) -> TargetingRule:
        """Create a new targeting rule."""
        return cls(
            id=uuid4(),
            feature_flag_id=feature_flag_id,
            priority=priority,
            attribute=attribute,
            operator=operator,
            value=value,
            result=result,
            description=description,
        )

    def evaluate(self, context: dict[str, Any]) -> tuple[bool, Any]:
        """Evaluate this rule against a context.

        Args:
            context: Dictionary of context values (e.g., {'user.email': 'test@example.com'})

        Returns:
            Tuple of (matches, result) - result is only meaningful if matches is True
        """
        # Get the attribute value from context using dot notation
        attr_value = self._get_nested_value(context, self.attribute)

        if attr_value is None:
            return False, None

        matches = self._evaluate_operator(attr_value)
        return matches, self.result if matches else None

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _evaluate_operator(self, attr_value: Any) -> bool:
        """Evaluate the operator against the attribute value."""
        attr_str = str(attr_value).lower()
        target_str = self.value.lower()

        match self.operator:
            case Operator.EQUALS:
                return attr_str == target_str
            case Operator.NOT_EQUALS:
                return attr_str != target_str
            case Operator.CONTAINS:
                return target_str in attr_str
            case Operator.NOT_CONTAINS:
                return target_str not in attr_str
            case Operator.STARTS_WITH:
                return attr_str.startswith(target_str)
            case Operator.ENDS_WITH:
                return attr_str.endswith(target_str)
            case Operator.REGEX:
                try:
                    return bool(re.match(self.value, str(attr_value)))
                except re.error:
                    return False
            case Operator.IN:
                values = [v.strip().lower() for v in self.value.split(",")]
                return attr_str in values
            case Operator.NOT_IN:
                values = [v.strip().lower() for v in self.value.split(",")]
                return attr_str not in values
            case Operator.GREATER_THAN:
                try:
                    return float(attr_value) > float(self.value)
                except (ValueError, TypeError):
                    return False
            case Operator.LESS_THAN:
                try:
                    return float(attr_value) < float(self.value)
                except (ValueError, TypeError):
                    return False
            case Operator.GREATER_THAN_OR_EQUAL:
                try:
                    return float(attr_value) >= float(self.value)
                except (ValueError, TypeError):
                    return False
            case Operator.LESS_THAN_OR_EQUAL:
                try:
                    return float(attr_value) <= float(self.value)
                except (ValueError, TypeError):
                    return False
            case _:
                return False


@dataclass
class FeatureFlag:
    """Aggregate root for feature flag management.

    Represents a feature toggle with targeting, rollout, and override capabilities.

    Attributes:
        id: Unique identifier
        name: Unique feature flag name
        description: Human-readable description
        enabled: Global enable/disable switch
        default_value: Default value when no rules match
        rollout_percentage: Percentage of users to enable for
        targeting_rules: List of targeting rules (evaluated in order)
        tenant_overrides: Per-tenant enable/disable overrides
        environment_overrides: Per-environment enable/disable overrides
        expires_at: Optional expiration datetime
        tags: List of tags for categorization
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the flag
        updated_by: User who last updated the flag
    """

    id: UUID
    name: FeatureName
    description: str | None = None
    enabled: bool = False
    default_value: Any = False  # Can be bool, str, int, dict
    rollout_percentage: Percentage = field(default_factory=Percentage.full)
    targeting_rules: list[TargetingRule] = field(default_factory=list)
    tenant_overrides: dict[str, Any] = field(default_factory=dict)
    environment_overrides: dict[Environment, Any] = field(default_factory=dict)
    expires_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def create(
        cls,
        name: str | FeatureName,
        description: str | None = None,
        enabled: bool = False,
        default_value: Any = False,
        rollout_percentage: int | Percentage = 100,
        expires_at: datetime | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
    ) -> FeatureFlag:
        """Create a new feature flag.

        Args:
            name: Unique name for the feature flag
            description: Human-readable description
            enabled: Whether the flag is globally enabled
            default_value: Default value when no rules match
            rollout_percentage: Percentage of users to enable (0-100)
            expires_at: Optional expiration datetime
            tags: Optional list of tags
            created_by: User creating the flag

        Returns:
            A new FeatureFlag instance
        """
        name_vo = name if isinstance(name, FeatureName) else FeatureName(name)
        percentage_vo = (
            rollout_percentage
            if isinstance(rollout_percentage, Percentage)
            else Percentage(rollout_percentage)
        )

        now = datetime.now(UTC)

        return cls(
            id=uuid4(),
            name=name_vo,
            description=description,
            enabled=enabled,
            default_value=default_value,
            rollout_percentage=percentage_vo,
            targeting_rules=[],
            tenant_overrides={},
            environment_overrides={},
            expires_at=expires_at,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
        )

    def evaluate(
        self,
        context: dict[str, Any] | None = None,
        tenant_id: str | TenantId | None = None,
        environment: Environment | None = None,
    ) -> Any:
        """Evaluate the feature flag for the given context.

        Evaluation order:
        1. Check if expired -> return default_value
        2. Check if globally disabled -> return default_value
        3. Check tenant override -> return override if exists
        4. Check environment override -> return override if exists
        5. Evaluate targeting rules -> return first match
        6. Check rollout percentage -> return enabled/default based on hash
        7. Return default_value

        Args:
            context: Dictionary of context values for targeting
            tenant_id: Optional tenant identifier
            environment: Optional environment

        Returns:
            The evaluated feature flag value
        """
        # 1. Check expiration
        if self.is_expired:
            return self.default_value

        # 2. Check if globally disabled
        if not self.enabled:
            return self.default_value

        # 3. Check tenant override
        if tenant_id:
            tenant_key = str(tenant_id)
            if tenant_key in self.tenant_overrides:
                return self.tenant_overrides[tenant_key]

        # 4. Check environment override
        if environment and environment in self.environment_overrides:
            return self.environment_overrides[environment]

        # 5. Evaluate targeting rules (in priority order)
        if context and self.targeting_rules:
            sorted_rules = sorted(self.targeting_rules, key=lambda r: r.priority)
            for rule in sorted_rules:
                matches, result = rule.evaluate(context)
                if matches:
                    return result

        # 6. Check rollout percentage
        if not self.rollout_percentage.is_full():
            # Use consistent hashing based on user identifier
            user_id = self._get_user_identifier(context)
            if user_id:
                if not self._is_in_rollout(user_id):
                    return self.default_value
            else:
                # No user identifier - default to not in rollout for safety
                return self.default_value

        # 7. Return default (flag is enabled and user is in rollout)
        return True if isinstance(self.default_value, bool) else self.default_value

    def _get_user_identifier(self, context: dict[str, Any] | None) -> str | None:
        """Extract a user identifier from context for consistent rollout."""
        if not context:
            return None

        # Try common user identifier fields
        for field_path in ["user.id", "user_id", "userId", "user.email", "email"]:
            value = self._get_nested_value(context, field_path)
            if value:
                return str(value)

        return None

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _is_in_rollout(self, user_id: str) -> bool:
        """Check if a user is in the rollout percentage using consistent hashing."""
        # Create a consistent hash of the user ID and feature name
        hash_input = f"{self.name.value}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        bucket = hash_value % 100

        return bucket < self.rollout_percentage.value

    def add_targeting_rule(
        self,
        attribute: str,
        operator: Operator,
        value: str,
        result: Any,
        priority: int | None = None,
        description: str | None = None,
    ) -> TargetingRule:
        """Add a targeting rule to the feature flag.

        Args:
            attribute: The context attribute to check
            operator: The comparison operator
            value: The value to compare against
            result: The value to return if rule matches
            priority: Rule priority (defaults to next available)
            description: Optional description

        Returns:
            The created targeting rule
        """
        if priority is None:
            priority = len(self.targeting_rules)

        rule = TargetingRule.create(
            feature_flag_id=self.id,
            priority=priority,
            attribute=attribute,
            operator=operator,
            value=value,
            result=result,
            description=description,
        )

        self.targeting_rules.append(rule)
        self.updated_at = datetime.now(UTC)

        return rule

    def remove_targeting_rule(self, rule_id: UUID) -> bool:
        """Remove a targeting rule by ID."""
        for rule in self.targeting_rules:
            if rule.id == rule_id:
                self.targeting_rules.remove(rule)
                self.updated_at = datetime.now(UTC)
                return True
        return False

    def set_tenant_override(self, tenant_id: str | TenantId, value: Any) -> None:
        """Set an override value for a specific tenant."""
        tenant_key = str(tenant_id)
        self.tenant_overrides[tenant_key] = value
        self.updated_at = datetime.now(UTC)

    def remove_tenant_override(self, tenant_id: str | TenantId) -> bool:
        """Remove a tenant override."""
        tenant_key = str(tenant_id)
        if tenant_key in self.tenant_overrides:
            del self.tenant_overrides[tenant_key]
            self.updated_at = datetime.now(UTC)
            return True
        return False

    def set_environment_override(self, environment: Environment, value: Any) -> None:
        """Set an override value for a specific environment."""
        self.environment_overrides[environment] = value
        self.updated_at = datetime.now(UTC)

    def remove_environment_override(self, environment: Environment) -> bool:
        """Remove an environment override."""
        if environment in self.environment_overrides:
            del self.environment_overrides[environment]
            self.updated_at = datetime.now(UTC)
            return True
        return False

    def enable(self, updated_by: str | None = None) -> None:
        """Enable the feature flag."""
        self.enabled = True
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    def disable(self, updated_by: str | None = None) -> None:
        """Disable the feature flag."""
        self.enabled = False
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    def set_rollout_percentage(
        self,
        percentage: int | Percentage,
        updated_by: str | None = None,
    ) -> None:
        """Set the rollout percentage."""
        self.rollout_percentage = (
            percentage if isinstance(percentage, Percentage) else Percentage(percentage)
        )
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    @property
    def is_expired(self) -> bool:
        """Check if the feature flag has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def rule_count(self) -> int:
        """Get the number of targeting rules."""
        return len(self.targeting_rules)
