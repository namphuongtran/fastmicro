"""Domain value objects for metastore service.

Value objects are immutable and defined by their attributes, not identity.
They encapsulate validation and business rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    """Supported content types for metadata values."""

    JSON = "application/json"
    YAML = "application/yaml"
    TEXT = "text/plain"
    BINARY = "application/octet-stream"
    XML = "application/xml"
    PROPERTIES = "text/x-java-properties"


class Environment(str, Enum):
    """Deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Operator(str, Enum):
    """Operators for targeting rules in feature flags."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


@dataclass(frozen=True)
class MetadataKey:
    """Represents a metadata key.

    Keys must be alphanumeric with dots, dashes, and underscores.
    Maximum 255 characters.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the metadata key."""
        if not self.value:
            raise ValueError("Metadata key cannot be empty")
        if len(self.value) > 255:
            raise ValueError("Metadata key cannot exceed 255 characters")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", self.value):
            raise ValueError(
                "Metadata key must start with a letter and contain only "
                "alphanumeric characters, dots, dashes, and underscores"
            )

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MetadataKey):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class Namespace:
    """Represents a namespace for grouping related metadata.

    Namespaces are hierarchical, separated by dots (e.g., 'app.service.config').
    """

    value: str

    DEFAULT = "default"

    def __post_init__(self) -> None:
        """Validate the namespace."""
        if not self.value:
            object.__setattr__(self, "value", self.DEFAULT)
            return
        if len(self.value) > 100:
            raise ValueError("Namespace cannot exceed 100 characters")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", self.value):
            raise ValueError(
                "Namespace must start with a letter and contain only "
                "alphanumeric characters, dots, dashes, and underscores"
            )

    def __str__(self) -> str:
        return self.value

    @classmethod
    def default(cls) -> Namespace:
        """Create the default namespace."""
        return cls(cls.DEFAULT)

    def is_child_of(self, parent: Namespace) -> bool:
        """Check if this namespace is a child of another."""
        return self.value.startswith(f"{parent.value}.")

    def parent(self) -> Namespace | None:
        """Get the parent namespace."""
        if "." not in self.value:
            return None
        parent_value = ".".join(self.value.split(".")[:-1])
        return Namespace(parent_value)


@dataclass(frozen=True)
class TenantId:
    """Represents a tenant identifier for multi-tenancy support.

    Tenant IDs are UUIDs or alphanumeric strings.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the tenant ID."""
        if not self.value:
            raise ValueError("Tenant ID cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Tenant ID cannot exceed 100 characters")
        # Allow UUID format or alphanumeric
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        alphanumeric_pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
        if not (
            re.match(uuid_pattern, self.value, re.IGNORECASE)
            or re.match(alphanumeric_pattern, self.value)
        ):
            raise ValueError("Tenant ID must be a valid UUID or alphanumeric string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FeatureName:
    """Represents a feature flag name.

    Feature names must be alphanumeric with dashes and underscores.
    Typically in kebab-case (e.g., 'new-dashboard', 'beta-feature').
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the feature name."""
        if not self.value:
            raise ValueError("Feature name cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Feature name cannot exceed 100 characters")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", self.value):
            raise ValueError(
                "Feature name must start with a letter and contain only "
                "alphanumeric characters, dashes, and underscores"
            )

    def __str__(self) -> str:
        return self.value

    def to_snake_case(self) -> str:
        """Convert to snake_case for use in code."""
        return self.value.replace("-", "_").lower()


@dataclass(frozen=True)
class Percentage:
    """Represents a percentage value (0-100).

    Used for feature flag rollout percentages.
    """

    value: int

    def __post_init__(self) -> None:
        """Validate the percentage."""
        if not isinstance(self.value, int):
            raise TypeError("Percentage must be an integer")
        if self.value < 0 or self.value > 100:
            raise ValueError("Percentage must be between 0 and 100")

    def __str__(self) -> str:
        return f"{self.value}%"

    def __int__(self) -> int:
        return self.value

    @classmethod
    def full(cls) -> Percentage:
        """Create 100% rollout."""
        return cls(100)

    @classmethod
    def zero(cls) -> Percentage:
        """Create 0% rollout."""
        return cls(0)

    def is_full(self) -> bool:
        """Check if this is a full rollout."""
        return self.value == 100

    def is_zero(self) -> bool:
        """Check if this is zero rollout."""
        return self.value == 0


@dataclass(frozen=True)
class Tag:
    """Represents a tag for categorizing metadata.

    Tags are lowercase alphanumeric with dashes.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the tag."""
        if not self.value:
            raise ValueError("Tag cannot be empty")
        if len(self.value) > 50:
            raise ValueError("Tag cannot exceed 50 characters")
        # Normalize to lowercase
        normalized = self.value.lower()
        if not re.match(r"^[a-z][a-z0-9-]*$", normalized):
            raise ValueError(
                "Tag must start with a letter and contain only "
                "lowercase alphanumeric characters and dashes"
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Version:
    """Represents a semantic version number."""

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        """Validate version numbers."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version numbers cannot be negative")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse a version string."""
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be in format 'major.minor.patch'")
        try:
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            raise ValueError("Version numbers must be integers")

    @classmethod
    def initial(cls) -> Version:
        """Create initial version 1.0.0."""
        return cls(1, 0, 0)

    def bump_major(self) -> Version:
        """Bump major version."""
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        """Bump minor version."""
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        """Bump patch version."""
        return Version(self.major, self.minor, self.patch + 1)


@dataclass(frozen=True)
class MetadataValue:
    """Represents a metadata value with type information.

    Supports JSON-serializable values with content type awareness.
    """

    raw_value: Any
    content_type: ContentType = ContentType.JSON

    def __str__(self) -> str:
        return str(self.raw_value)

    def as_dict(self) -> dict:
        """Get value as dictionary (for JSON content)."""
        if isinstance(self.raw_value, dict):
            return self.raw_value
        raise TypeError("Value is not a dictionary")

    def as_list(self) -> list:
        """Get value as list (for JSON content)."""
        if isinstance(self.raw_value, list):
            return self.raw_value
        raise TypeError("Value is not a list")

    def as_string(self) -> str:
        """Get value as string."""
        return str(self.raw_value)

    def as_int(self) -> int:
        """Get value as integer."""
        return int(self.raw_value)

    def as_float(self) -> float:
        """Get value as float."""
        return float(self.raw_value)

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if isinstance(self.raw_value, bool):
            return self.raw_value
        if isinstance(self.raw_value, str):
            return self.raw_value.lower() in ("true", "yes", "1", "on")
        return bool(self.raw_value)
