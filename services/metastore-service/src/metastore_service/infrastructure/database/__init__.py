"""Database package.

Provides database models and session management using the shared library's
AsyncDatabaseManager for consistent connection pooling and transaction handling.
"""

from metastore_service.infrastructure.database.models import (
    Base,
    ConfigurationModel,
    ConfigurationSchemaModel,
    ConfigurationVersionModel,
    FeatureFlagModel,
    MetadataEntryModel,
    MetadataVersionModel,
    TargetingRuleModel,
)

# Re-export shared library database utilities
from shared.sqlalchemy_async import AsyncDatabaseManager, DatabaseConfig

__all__ = [
    # Models
    "Base",
    "MetadataEntryModel",
    "MetadataVersionModel",
    "FeatureFlagModel",
    "TargetingRuleModel",
    "ConfigurationModel",
    "ConfigurationVersionModel",
    "ConfigurationSchemaModel",
    # Database management (from shared library)
    "AsyncDatabaseManager",
    "DatabaseConfig",
]
