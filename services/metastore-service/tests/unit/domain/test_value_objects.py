"""Tests for domain value objects."""

import pytest

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


class TestMetadataKey:
    """Tests for MetadataKey value object."""

    def test_valid_key(self):
        """Test creating a valid metadata key."""
        key = MetadataKey("app.config.database")
        assert key.value == "app.config.database"

    def test_key_with_hyphens(self):
        """Test key with hyphens."""
        key = MetadataKey("my-app-config")
        assert key.value == "my-app-config"

    def test_key_with_underscores(self):
        """Test key with underscores."""
        key = MetadataKey("my_app_config")
        assert key.value == "my_app_config"

    def test_empty_key_raises_error(self):
        """Test that empty key raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            MetadataKey("")

    def test_key_with_spaces_raises_error(self):
        """Test that key with spaces raises ValueError."""
        with pytest.raises(ValueError, match="must start with a letter"):
            MetadataKey("my config key")


class TestNamespace:
    """Tests for Namespace value object."""

    def test_valid_namespace(self):
        """Test creating a valid namespace."""
        ns = Namespace("production")
        assert ns.value == "production"

    def test_empty_namespace_defaults_to_default(self):
        """Test that empty namespace defaults to 'default'."""
        ns = Namespace("")
        assert ns.value == "default"


class TestTenantId:
    """Tests for TenantId value object."""

    def test_valid_tenant_id(self):
        """Test creating a valid tenant ID."""
        tenant = TenantId("tenant-123")
        assert tenant.value == "tenant-123"

    def test_empty_tenant_id_raises_error(self):
        """Test that empty tenant ID raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TenantId("")


class TestFeatureName:
    """Tests for FeatureName value object."""

    def test_valid_feature_name(self):
        """Test creating a valid feature name."""
        name = FeatureName("new-checkout-flow")
        assert name.value == "new-checkout-flow"

    def test_feature_name_with_underscores(self):
        """Test feature name with underscores."""
        name = FeatureName("feature_dark_mode")
        assert name.value == "feature_dark_mode"

    def test_empty_feature_name_raises_error(self):
        """Test that empty feature name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FeatureName("")


class TestPercentage:
    """Tests for Percentage value object."""

    def test_valid_percentage(self):
        """Test creating a valid percentage."""
        pct = Percentage(50)
        assert pct.value == 50

    def test_zero_percentage(self):
        """Test zero percentage."""
        pct = Percentage(0)
        assert pct.value == 0

    def test_hundred_percentage(self):
        """Test 100 percentage."""
        pct = Percentage(100)
        assert pct.value == 100

    def test_negative_percentage_raises_error(self):
        """Test that negative percentage raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Percentage(-1)

    def test_over_hundred_percentage_raises_error(self):
        """Test that percentage over 100 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Percentage(101)


class TestTag:
    """Tests for Tag value object."""

    def test_valid_tag(self):
        """Test creating a valid tag."""
        tag = Tag("production")
        assert tag.value == "production"

    def test_empty_tag_raises_error(self):
        """Test that empty tag raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Tag("")


class TestVersion:
    """Tests for Version value object."""

    def test_valid_version(self):
        """Test creating a valid version."""
        version = Version(1, 0, 0)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert str(version) == "1.0.0"

    def test_initial_version(self):
        """Test initial version factory."""
        version = Version.initial()
        assert str(version) == "1.0.0"

    def test_negative_version_raises_error(self):
        """Test that negative version raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Version(-1, 0, 0)


class TestMetadataValue:
    """Tests for MetadataValue value object."""

    def test_json_value(self):
        """Test creating a JSON metadata value."""
        value = MetadataValue(
            raw_value={"key": "value"},
            content_type=ContentType.JSON,
        )
        assert value.raw_value == {"key": "value"}
        assert value.content_type == ContentType.JSON

    def test_string_value(self):
        """Test creating a string metadata value."""
        value = MetadataValue(
            raw_value="hello world",
            content_type=ContentType.TEXT,
        )
        assert value.raw_value == "hello world"
        assert value.content_type == ContentType.TEXT

    def test_binary_value(self):
        """Test creating a binary metadata value."""
        value = MetadataValue(
            raw_value=b"binary data",
            content_type=ContentType.BINARY,
        )
        assert value.raw_value == b"binary data"
        assert value.content_type == ContentType.BINARY


class TestEnums:
    """Tests for enum value objects."""

    def test_content_types(self):
        """Test ContentType enum values."""
        assert ContentType.JSON.value == "application/json"
        assert ContentType.TEXT.value == "text/plain"
        assert ContentType.YAML.value == "application/yaml"
        assert ContentType.BINARY.value == "application/octet-stream"

    def test_environments(self):
        """Test Environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_operators(self):
        """Test Operator enum values."""
        assert Operator.EQUALS.value == "eq"
        assert Operator.NOT_EQUALS.value == "neq"
        assert Operator.CONTAINS.value == "contains"
        assert Operator.IN.value == "in"
        assert Operator.GREATER_THAN.value == "gt"
        assert Operator.LESS_THAN.value == "lt"
