"""Tests for application services."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from metastore_service.application.dtos.metadata_dtos import (
    CreateMetadataDTO,
    UpdateMetadataDTO,
)
from metastore_service.application.dtos.feature_flag_dtos import (
    CreateFeatureFlagDTO,
    EvaluateFeatureFlagDTO,
    UpdateFeatureFlagDTO,
)
from metastore_service.application.dtos.configuration_dtos import (
    CreateConfigurationDTO,
    UpdateConfigurationDTO,
)
from metastore_service.application.services.metadata_service import MetadataService
from metastore_service.application.services.feature_flag_service import FeatureFlagService
from metastore_service.application.services.configuration_service import ConfigurationService
from metastore_service.domain.entities.metadata import MetadataEntry
from metastore_service.domain.entities.feature_flag import FeatureFlag
from metastore_service.domain.entities.configuration import Configuration
from metastore_service.domain.value_objects import (
    ContentType,
    Environment,
    FeatureName,
    MetadataKey,
    MetadataValue,
    Namespace,
    Percentage,
)
from shared.cache.backends.null import NullCache


class TestMetadataService:
    """Tests for MetadataService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock metadata repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create a metadata service with mock repository."""
        return MetadataService(mock_repository, NullCache())

    @pytest.mark.asyncio
    async def test_create_metadata(self, service, mock_repository):
        """Test creating metadata via service."""
        dto = CreateMetadataDTO(
            key="app.config",
            namespace="production",
            value={"setting": "value"},
            content_type=ContentType.JSON,
            tags=["config"],
            description="Test config",
        )

        mock_repository.exists.return_value = False
        mock_repository.create.return_value = MetadataEntry.create(
            key=MetadataKey(dto.key),
            namespace=Namespace(dto.namespace),
            value=dto.value,
            content_type=ContentType.JSON,
            tags=dto.tags,
            description=dto.description,
        )

        result = await service.create(dto)

        assert result.key == "app.config"
        assert result.namespace == "production"
        mock_repository.exists.assert_called_once()
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_metadata_raises_error(self, service, mock_repository):
        """Test that creating duplicate metadata raises an error."""
        dto = CreateMetadataDTO(
            key="app.config",
            namespace="production",
            value={"setting": "value"},
            content_type=ContentType.JSON,
        )

        mock_repository.exists.return_value = True

        with pytest.raises(ValueError, match="already exists"):
            await service.create(dto)

    @pytest.mark.asyncio
    async def test_get_metadata_by_id(self, service, mock_repository):
        """Test getting metadata by ID."""
        metadata_id = uuid4()
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value=MetadataValue(raw_value={"key": "value"}, content_type=ContentType.JSON),
            created_by="test-user",
        )
        entry.id = metadata_id

        mock_repository.get_by_id.return_value = entry

        result = await service.get_by_id(metadata_id)

        assert result is not None
        assert result.key == "app.config"
        mock_repository.get_by_id.assert_called_once_with(metadata_id)

    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self, service, mock_repository):
        """Test getting non-existent metadata."""
        mock_repository.get_by_id.return_value = None

        result = await service.get_by_id(uuid4())

        assert result is None


class TestFeatureFlagService:
    """Tests for FeatureFlagService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock feature flag repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create a feature flag service with mock repository."""
        return FeatureFlagService(mock_repository, NullCache())

    @pytest.mark.asyncio
    async def test_create_feature_flag(self, service, mock_repository):
        """Test creating a feature flag via service."""
        dto = CreateFeatureFlagDTO(
            name="new-feature",
            description="A new feature",
            enabled=True,
            default_value=True,
            rollout_percentage=50,
        )

        mock_repository.exists.return_value = False
        mock_repository.create.return_value = FeatureFlag.create(
            name=dto.name,
            description=dto.description,
            enabled=dto.enabled,
            default_value=dto.default_value,
            rollout_percentage=dto.rollout_percentage,
            created_by="test-user",
        )

        result = await service.create(dto, created_by="test-user")

        assert result.name == "new-feature"
        assert result.enabled is True
        mock_repository.exists.assert_called_once()
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_feature_flag(self, service, mock_repository):
        """Test evaluating a feature flag."""
        flag = FeatureFlag.create(
            name="test-flag",
            enabled=True,
            default_value=True,
            rollout_percentage=100,
            created_by="test-user",
        )

        mock_repository.get_by_name.return_value = flag

        evaluation = EvaluateFeatureFlagDTO(context={"user_id": "123"})
        result = await service.evaluate("test-flag", evaluation)

        assert result is True

    @pytest.mark.asyncio
    async def test_enable_disable_feature_flag(self, service, mock_repository):
        """Test enabling and disabling a feature flag."""
        flag_id = uuid4()
        flag = FeatureFlag.create(
            name="test-flag",
            enabled=False,
            default_value=True,
            created_by="test-user",
        )
        flag.id = flag_id

        # The service's enable method delegates to repository.enable
        mock_repository.enable.return_value = True
        mock_repository.get_by_id.return_value = flag

        result = await service.enable(flag_id, "admin-user")

        assert result is True
        mock_repository.enable.assert_called_once_with(flag_id, "admin-user")


class TestConfigurationService:
    """Tests for ConfigurationService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock configuration repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_schema_repository(self):
        """Create a mock schema repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository, mock_schema_repository):
        """Create a configuration service with mock repositories."""
        return ConfigurationService(mock_repository, mock_schema_repository, NullCache())

    @pytest.mark.asyncio
    async def test_create_configuration(self, service, mock_repository):
        """Test creating a configuration via service."""
        dto = CreateConfigurationDTO(
            service_id="my-service",
            name="app-config",
            environment=Environment.DEVELOPMENT,
            values={"host": "localhost", "port": 5432},
            description="App configuration",
        )

        mock_repository.exists.return_value = False
        mock_repository.create.return_value = Configuration.create(
            service_id=dto.service_id,
            name=dto.name,
            environment=dto.environment,
            values=dto.values,
            description=dto.description,
            created_by="test-user",
        )

        result = await service.create(dto, created_by="test-user")

        assert result.service_id == "my-service"
        assert result.name == "app-config"
        mock_repository.exists.assert_called_once()
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_effective_config(self, service, mock_repository):
        """Test getting effective configuration."""
        mock_repository.get_effective_config.return_value = {
            "host": "localhost",
            "port": 5432,
            "pool_size": 10,
        }

        result = await service.get_effective_config(
            "my-service",
            Environment.DEVELOPMENT,
        )

        assert result["host"] == "localhost"
        assert result["port"] == 5432
