"""Repository interfaces package."""

from metastore_service.domain.repositories.metadata_repository import (
    IMetadataRepository,
)
from metastore_service.domain.repositories.feature_flag_repository import (
    IFeatureFlagRepository,
)
from metastore_service.domain.repositories.configuration_repository import (
    IConfigurationRepository,
)

__all__ = [
    "IMetadataRepository",
    "IFeatureFlagRepository",
    "IConfigurationRepository",
]
