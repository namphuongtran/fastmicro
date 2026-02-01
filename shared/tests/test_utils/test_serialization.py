"""Tests for shared.utils.serialization module.

This module tests JSON serialization utilities including custom encoders,
datetime handling, and safe serialization with error handling.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel

from shared.utils.serialization import (
    CustomJSONEncoder,
    deserialize_json,
    safe_serialize,
    serialize_json,
)


class SampleEnum(Enum):
    """Sample enum for testing."""
    VALUE_A = "a"
    VALUE_B = "b"


class SamplePydanticModel(BaseModel):
    """Sample Pydantic model for testing."""
    name: str
    value: int


@dataclass
class SampleDataclass:
    """Sample dataclass for testing."""
    name: str
    value: int


class TestCustomJSONEncoder:
    """Tests for CustomJSONEncoder class."""

    def test_encodes_datetime(self) -> None:
        """Should encode datetime to ISO8601 string."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=datetime.UTC)
        result = json.dumps({"dt": dt}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert "2024-01-15" in parsed["dt"]

    def test_encodes_date(self) -> None:
        """Should encode date to ISO8601 string."""
        d = datetime.date(2024, 1, 15)
        result = json.dumps({"date": d}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["date"] == "2024-01-15"

    def test_encodes_time(self) -> None:
        """Should encode time to ISO8601 string."""
        t = datetime.time(10, 30, 45)
        result = json.dumps({"time": t}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert "10:30:45" in parsed["time"]

    def test_encodes_uuid(self) -> None:
        """Should encode UUID to string."""
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        result = json.dumps({"uuid": uuid_val}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["uuid"] == "12345678-1234-5678-1234-567812345678"

    def test_encodes_decimal(self) -> None:
        """Should encode Decimal to float."""
        decimal_val = Decimal("123.456")
        result = json.dumps({"decimal": decimal_val}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["decimal"] == 123.456

    def test_encodes_enum(self) -> None:
        """Should encode Enum to its value."""
        result = json.dumps({"enum": SampleEnum.VALUE_A}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["enum"] == "a"

    def test_encodes_set(self) -> None:
        """Should encode set to list."""
        result = json.dumps({"set": {1, 2, 3}}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert sorted(parsed["set"]) == [1, 2, 3]

    def test_encodes_frozenset(self) -> None:
        """Should encode frozenset to list."""
        result = json.dumps({"frozenset": frozenset([1, 2, 3])}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert sorted(parsed["frozenset"]) == [1, 2, 3]

    def test_encodes_bytes(self) -> None:
        """Should encode bytes to base64 string."""
        data = b"hello world"
        result = json.dumps({"bytes": data}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert isinstance(parsed["bytes"], str)

    def test_encodes_pydantic_model(self) -> None:
        """Should encode Pydantic model to dict."""
        model = SamplePydanticModel(name="test", value=42)
        result = json.dumps({"model": model}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["model"]["name"] == "test"
        assert parsed["model"]["value"] == 42

    def test_encodes_dataclass(self) -> None:
        """Should encode dataclass to dict."""
        dc = SampleDataclass(name="test", value=42)
        result = json.dumps({"dc": dc}, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["dc"]["name"] == "test"
        assert parsed["dc"]["value"] == 42

    def test_raises_on_unknown_type(self) -> None:
        """Should raise TypeError for unknown types."""
        class UnknownType:
            pass

        with pytest.raises(TypeError):
            json.dumps({"obj": UnknownType()}, cls=CustomJSONEncoder)


class TestSerializeJson:
    """Tests for serialize_json function."""

    def test_serializes_dict(self) -> None:
        """Should serialize dict to JSON string."""
        data = {"name": "test", "value": 42}
        result = serialize_json(data)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == data

    def test_serializes_list(self) -> None:
        """Should serialize list to JSON string."""
        data = [1, 2, 3]
        result = serialize_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_pretty_print_option(self) -> None:
        """Should support pretty print option."""
        data = {"a": 1, "b": 2}
        result = serialize_json(data, pretty=True)
        assert "\n" in result
        assert "  " in result  # Indentation

    def test_handles_nested_objects(self) -> None:
        """Should handle nested complex objects."""
        data = {
            "datetime": datetime.datetime(2024, 1, 15, tzinfo=datetime.UTC),
            "nested": {
                "uuid": UUID("12345678-1234-5678-1234-567812345678"),
                "decimal": Decimal("99.99"),
            }
        }
        result = serialize_json(data)
        parsed = json.loads(result)
        assert "2024-01-15" in parsed["datetime"]
        assert parsed["nested"]["decimal"] == 99.99


class TestDeserializeJson:
    """Tests for deserialize_json function."""

    def test_deserializes_to_dict(self) -> None:
        """Should deserialize JSON string to dict."""
        json_str = '{"name": "test", "value": 42}'
        result = deserialize_json(json_str)
        assert result == {"name": "test", "value": 42}

    def test_deserializes_to_list(self) -> None:
        """Should deserialize JSON string to list."""
        json_str = '[1, 2, 3]'
        result = deserialize_json(json_str)
        assert result == [1, 2, 3]

    def test_raises_on_invalid_json(self) -> None:
        """Should raise ValueError on invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            deserialize_json("not valid json")

    def test_handles_unicode(self) -> None:
        """Should handle unicode characters."""
        json_str = '{"name": "日本語"}'
        result = deserialize_json(json_str)
        assert result["name"] == "日本語"


class TestSafeSerialize:
    """Tests for safe_serialize function."""

    def test_returns_json_for_valid_data(self) -> None:
        """Should return JSON string for valid data."""
        data = {"name": "test"}
        result = safe_serialize(data)
        assert result == '{"name": "test"}'

    def test_returns_fallback_for_invalid_data(self) -> None:
        """Should return fallback string for unserializable data."""
        class Unserializable:
            pass

        result = safe_serialize(Unserializable())
        assert isinstance(result, str)
        assert "error" in result.lower() or "unserializable" in result.lower() or "Unserializable" in result

    def test_custom_fallback(self) -> None:
        """Should use custom fallback when provided."""
        class Unserializable:
            pass

        result = safe_serialize(Unserializable(), fallback="<failed>")
        assert result == "<failed>"

    def test_handles_circular_reference(self) -> None:
        """Should handle circular references gracefully."""
        data: dict[str, Any] = {"self": None}
        data["self"] = data  # Circular reference

        result = safe_serialize(data)
        # Should return fallback or truncated representation
        assert isinstance(result, str)
