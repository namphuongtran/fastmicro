"""Infrastructure layer package.

Contains database models, repository implementations, and external service integrations.
Uses shared library for database management and caching.
"""

from metastore_service.infrastructure.database.models import (
    MetadataEntryModel,
    MetadataVersionModel,
    FeatureFlagModel,
    TargetingRuleModel,
    ConfigurationModel,
    ConfigurationVersionModel,
    ConfigurationSchemaModel,
)

from metastore_service.infrastructure.repositories import (
    PostgresMetadataRepository,
    PostgresFeatureFlagRepository,
    PostgresConfigurationRepository,
)

# Re-export shared library cache and database utilities
from metastore_service.infrastructure.cache import (
    TieredCacheManager,
    CacheConfig,
)

from metastore_service.infrastructure.database import (
    AsyncDatabaseManager,
    DatabaseConfig,
)

__all__ = [
    # Database Models
    "MetadataEntryModel",
    "MetadataVersionModel",
    "FeatureFlagModel",
    "TargetingRuleModel",
    "ConfigurationModel",
    "ConfigurationVersionModel",
    "ConfigurationSchemaModel",
    # Repositories
    "PostgresMetadataRepository",
    "PostgresFeatureFlagRepository",
    "PostgresConfigurationRepository",
    # Cache (from shared library)
    "TieredCacheManager",
    "CacheConfig",
    # Database (from shared library)
    "AsyncDatabaseManager",
    "DatabaseConfig",
]
