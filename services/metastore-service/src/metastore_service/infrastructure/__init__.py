"""Infrastructure layer package.

Contains database models, repository implementations, and external service integrations.
Uses shared library for database management and caching.
"""

# Re-export shared library cache and database utilities
from metastore_service.infrastructure.cache import (
    CacheConfig,
    TieredCacheManager,
)
from metastore_service.infrastructure.database import (
    AsyncDatabaseManager,
    DatabaseConfig,
)
from metastore_service.infrastructure.database.models import (
    ConfigurationModel,
    ConfigurationSchemaModel,
    ConfigurationVersionModel,
    FeatureFlagModel,
    MetadataEntryModel,
    MetadataVersionModel,
    TargetingRuleModel,
)
from metastore_service.infrastructure.repositories import (
    PostgresConfigurationRepository,
    PostgresFeatureFlagRepository,
    PostgresMetadataRepository,
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
