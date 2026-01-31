"""Tests for domain entities."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from metastore_service.domain.entities.metadata import MetadataEntry, MetadataVersion
from metastore_service.domain.entities.feature_flag import FeatureFlag, TargetingRule
from metastore_service.domain.entities.configuration import Configuration, ConfigurationSchema
from metastore_service.domain.value_objects import (
    ContentType,
    Environment,
    FeatureName,
    MetadataKey,
    MetadataValue,
    Namespace,
    Operator,
    Percentage,
    TenantId,
)


class TestMetadataEntry:
    """Tests for MetadataEntry aggregate root."""

    def test_create_metadata_entry(self):
        """Test creating a metadata entry."""
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value={"setting": "value"},
            content_type=ContentType.JSON,
            tags=["config", "important"],
            description="Test config",
            created_by="test-user",
        )

        assert entry.key.value == "app.config"
        assert entry.namespace.value == "production"
        assert entry.current_value.raw_value == {"setting": "value"}
        assert entry.content_type == ContentType.JSON
        assert entry.has_tag("config")
        assert entry.description == "Test config"
        assert entry.created_by == "test-user"
        assert entry.current_version_number == 1
        assert len(entry.versions) == 1

    def test_update_metadata_value(self):
        """Test updating metadata value creates a new version."""
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value={"setting": "old"},
            content_type=ContentType.JSON,
            created_by="test-user",
        )

        entry.update_value(
            new_value={"setting": "new"},
            updated_by="another-user",
            change_reason="Updated setting",
        )

        assert entry.current_value.raw_value == {"setting": "new"}
        assert entry.current_version_number == 2
        assert len(entry.versions) == 2
        assert entry.updated_by == "another-user"

    def test_rollback_metadata(self):
        """Test rolling back to a previous version."""
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value="v1",
            content_type=ContentType.TEXT,
            created_by="test-user",
        )

        entry.update_value(new_value="v2", updated_by="test-user")
        entry.update_value(new_value="v3", updated_by="test-user")

        assert entry.current_version_number == 3

        entry.rollback_to_version(1, "test-user")

        # After rollback, we should have a new version (4) with the old value
        assert entry.current_version_number == 4
        assert entry.current_value.raw_value == "v1"

    def test_add_tags(self):
        """Test adding tags."""
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value="test",
            content_type=ContentType.TEXT,
            tags=["existing"],
            created_by="test-user",
        )

        entry.add_tag("new-tag")
        assert entry.has_tag("new-tag")
        assert entry.has_tag("existing")

    def test_remove_tags(self):
        """Test removing tags."""
        entry = MetadataEntry.create(
            key=MetadataKey("app.config"),
            namespace=Namespace("production"),
            value="test",
            content_type=ContentType.TEXT,
            tags=["tag1", "tag2"],
            created_by="test-user",
        )

        entry.remove_tag("tag1")
        assert not entry.has_tag("tag1")
        assert entry.has_tag("tag2")


class TestFeatureFlag:
    """Tests for FeatureFlag aggregate root."""

    def test_create_feature_flag(self):
        """Test creating a feature flag."""
        flag = FeatureFlag.create(
            name=FeatureName("new-feature"),
            description="A new feature",
            enabled=True,
            default_value=True,
            rollout_percentage=Percentage(50),
            created_by="test-user",
        )

        assert flag.name.value == "new-feature"
        assert flag.description == "A new feature"
        assert flag.enabled is True
        assert flag.default_value is True
        assert flag.rollout_percentage.value == 50

    def test_evaluate_disabled_flag(self):
        """Test evaluating a disabled feature flag."""
        flag = FeatureFlag.create(
            name=FeatureName("disabled-feature"),
            enabled=False,
            default_value=True,
            created_by="test-user",
        )

        result = flag.evaluate()
        assert result is True  # Returns default_value when disabled

    def test_evaluate_enabled_flag_100_percent_rollout(self):
        """Test evaluating a feature flag with 100% rollout."""
        flag = FeatureFlag.create(
            name=FeatureName("full-rollout"),
            enabled=True,
            default_value=True,
            rollout_percentage=Percentage(100),
            created_by="test-user",
        )

        result = flag.evaluate(context={"user_id": "123"})
        assert result is True

    def test_evaluate_enabled_flag_0_percent_rollout(self):
        """Test evaluating a feature flag with 0% rollout."""
        flag = FeatureFlag.create(
            name=FeatureName("no-rollout"),
            enabled=True,
            default_value=False,
            rollout_percentage=Percentage(0),
            created_by="test-user",
        )

        result = flag.evaluate(context={"user_id": "123"})
        assert result is False  # Returns default_value when outside rollout

    def test_evaluate_with_tenant_override(self):
        """Test evaluating with tenant-specific override."""
        flag = FeatureFlag.create(
            name=FeatureName("tenant-override"),
            enabled=True,
            default_value=False,
            rollout_percentage=Percentage(0),
            created_by="test-user",
        )

        flag.set_tenant_override("premium-tenant", True)

        # Without tenant - should follow rollout (0%) -> default_value
        result_no_tenant = flag.evaluate()
        assert result_no_tenant is False

        # With premium tenant - should get override
        result_premium = flag.evaluate(tenant_id="premium-tenant")
        assert result_premium is True

    def test_evaluate_with_environment_override(self):
        """Test evaluating with environment-specific override."""
        flag = FeatureFlag.create(
            name=FeatureName("env-override"),
            enabled=True,
            default_value=False,
            rollout_percentage=Percentage(0),
            created_by="test-user",
        )

        flag.set_environment_override(Environment.DEVELOPMENT, True)

        # Without environment - should follow rollout (0%) -> default_value
        result_no_env = flag.evaluate()
        assert result_no_env is False

        # With development env - should get override
        result_dev = flag.evaluate(environment=Environment.DEVELOPMENT)
        assert result_dev is True

    def test_add_targeting_rule(self):
        """Test adding a targeting rule."""
        flag = FeatureFlag.create(
            name=FeatureName("targeted-feature"),
            enabled=True,
            default_value=False,
            created_by="test-user",
        )

        flag.add_targeting_rule(
            attribute="user_role",
            operator=Operator.EQUALS,
            value="admin",
            result=True,
            priority=1,
        )

        assert len(flag.targeting_rules) == 1
        assert flag.targeting_rules[0].attribute == "user_role"

    def test_evaluate_with_targeting_rule(self):
        """Test evaluating with targeting rules."""
        flag = FeatureFlag.create(
            name=FeatureName("targeted-feature"),
            enabled=True,
            default_value=False,
            rollout_percentage=Percentage(0),
            created_by="test-user",
        )

        flag.add_targeting_rule(
            attribute="user_role",
            operator=Operator.EQUALS,
            value="admin",
            result=True,
            priority=1,
        )

        # Non-admin user
        result_user = flag.evaluate(context={"user_role": "user"})
        assert result_user is False

        # Admin user
        result_admin = flag.evaluate(context={"user_role": "admin"})
        assert result_admin is True


class TestConfiguration:
    """Tests for Configuration aggregate root."""

    def test_create_configuration(self):
        """Test creating a configuration."""
        config = Configuration.create(
            service_id="my-service",
            name="database-config",
            environment=Environment.DEVELOPMENT,
            values={"host": "localhost", "port": 5432},
            description="Database configuration",
            created_by="test-user",
        )

        assert config.service_id == "my-service"
        assert config.name == "database-config"
        assert config.environment == Environment.DEVELOPMENT
        assert config.values["host"] == "localhost"
        assert config.is_active is True
        assert config.current_version_number == 1

    def test_update_configuration_values(self):
        """Test updating configuration values."""
        config = Configuration.create(
            service_id="my-service",
            name="app-config",
            environment=Environment.DEVELOPMENT,
            values={"setting": "old"},
            created_by="test-user",
        )

        config.update_values(
            new_values={"setting": "new"},
            updated_by="another-user",
            change_reason="Updated setting",
        )

        assert config.values["setting"] == "new"
        assert config.current_version_number == 2
        assert len(config.versions) == 2

    def test_validate_against_schema(self):
        """Test validating configuration against a schema."""
        schema = ConfigurationSchema.create(
            name="db-schema",
            version="1.0.0",
            json_schema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["host", "port"],
            },
        )

        config = Configuration.create(
            service_id="my-service",
            name="db-config",
            environment=Environment.DEVELOPMENT,
            values={"host": "localhost", "port": 5432},
            schema=schema,
            created_by="test-user",
        )

        # Valid configuration - schema validation happens during create
        assert config.values["host"] == "localhost"
        assert config.values["port"] == 5432

    def test_activate_deactivate(self):
        """Test activating and deactivating configuration."""
        config = Configuration.create(
            service_id="my-service",
            name="app-config",
            environment=Environment.DEVELOPMENT,
            values={"key": "value"},
            created_by="test-user",
        )

        assert config.is_active is True

        config.deactivate("test-user")
        assert config.is_active is False

        config.activate("test-user")
        assert config.is_active is True

    def test_is_effective(self):
        """Test checking if configuration is effective."""
        config = Configuration.create(
            service_id="my-service",
            name="app-config",
            environment=Environment.DEVELOPMENT,
            values={"key": "value"},
            created_by="test-user",
        )

        assert config.is_effective is True

        config.deactivate("test-user")
        assert config.is_effective is False
