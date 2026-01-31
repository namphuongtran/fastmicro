"""Domain layer for metastore service.

Contains entities, value objects, repositories, and domain events
following Domain-Driven Design principles.
"""

# Value Objects
from metastore_service.domain.value_objects import (
    ContentType,
    Environment,
    FeatureName,
    MetadataKey,
    MetadataValue,
    Namespace,
    Operator,
    Percentage,
    Tag,
    TenantId,
    Version,
)

# Entities
from metastore_service.domain.entities import (
    Configuration,
    ConfigurationSchema,
    FeatureFlag,
    MetadataEntry,
    MetadataVersion,
    TargetingRule,
)

# Repository Interfaces
from metastore_service.domain.repositories import (
    IConfigurationRepository,
    IFeatureFlagRepository,
    IMetadataRepository,
)

__all__ = [
    # Value Objects
    "ContentType",
    "Environment",
    "FeatureName",
    "MetadataKey",
    "MetadataValue",
    "Namespace",
    "Operator",
    "Percentage",
    "Tag",
    "TenantId",
    "Version",
    # Entities
    "Configuration",
    "ConfigurationSchema",
    "FeatureFlag",
    "MetadataEntry",
    "MetadataVersion",
    "TargetingRule",
    # Repository Interfaces
    "IConfigurationRepository",
    "IFeatureFlagRepository",
    "IMetadataRepository",
]

