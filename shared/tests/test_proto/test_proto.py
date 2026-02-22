"""Tests for gRPC/Protobuf utilities."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from shared.proto.serialization import (
    ProtobufSerializer,
    pydantic_to_struct,
    struct_to_dict,
)
from shared.proto.status_mapping import (
    GrpcServiceConfig,
    grpc_status_to_http,
    http_status_to_grpc,
)


# ====================================================================
# ProtobufSerializer
# ====================================================================


class TestProtobufSerializer:
    def test_dict_to_struct_and_back(self):
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        struct_msg = ProtobufSerializer.dict_to_struct(data)
        result = ProtobufSerializer.struct_to_dict(struct_msg)
        assert result["key"] == "value"
        assert result["number"] == 42
        assert result["nested"]["a"] == 1

    def test_empty_dict(self):
        struct_msg = ProtobufSerializer.dict_to_struct({})
        result = ProtobufSerializer.struct_to_dict(struct_msg)
        assert result == {}

    def test_list_values(self):
        data = {"items": [1, 2, 3]}
        struct_msg = ProtobufSerializer.dict_to_struct(data)
        result = ProtobufSerializer.struct_to_dict(struct_msg)
        assert result["items"] == [1, 2, 3]

    def test_bool_values(self):
        data = {"active": True, "deleted": False}
        struct_msg = ProtobufSerializer.dict_to_struct(data)
        result = ProtobufSerializer.struct_to_dict(struct_msg)
        assert result["active"] is True
        assert result["deleted"] is False


class TestPydanticToStruct:
    def test_simple_model(self):
        class User(BaseModel):
            name: str
            age: int

        user = User(name="Alice", age=30)
        struct_msg = pydantic_to_struct(user)
        result = struct_to_dict(struct_msg)
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_nested_model(self):
        class Address(BaseModel):
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        person = Person(name="Bob", address=Address(city="NYC"))
        struct_msg = pydantic_to_struct(person)
        result = struct_to_dict(struct_msg)
        assert result["name"] == "Bob"
        assert result["address"]["city"] == "NYC"


# ====================================================================
# Status mapping
# ====================================================================


class TestGrpcStatusToHttp:
    @pytest.mark.parametrize(
        ("grpc_code", "expected_http"),
        [
            (0, 200),
            (3, 400),
            (5, 404),
            (7, 403),
            (13, 500),
            (14, 503),
            (16, 401),
        ],
    )
    def test_known_codes(self, grpc_code: int, expected_http: int):
        assert grpc_status_to_http(grpc_code) == expected_http

    def test_unknown_code_raises(self):
        with pytest.raises(ValueError, match="Unknown gRPC status code"):
            grpc_status_to_http(999)


class TestHttpStatusToGrpc:
    @pytest.mark.parametrize(
        ("http_code", "expected_grpc"),
        [
            (200, 0),
            (400, 3),
            (401, 16),
            (403, 7),
            (404, 5),
            (500, 13),
            (503, 14),
        ],
    )
    def test_known_codes(self, http_code: int, expected_grpc: int):
        assert http_status_to_grpc(http_code) == expected_grpc

    def test_unknown_code_raises(self):
        with pytest.raises(ValueError, match="No gRPC mapping"):
            http_status_to_grpc(418)


# ====================================================================
# GrpcServiceConfig
# ====================================================================


class TestGrpcServiceConfig:
    def test_defaults(self):
        cfg = GrpcServiceConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 50051
        assert cfg.max_workers == 10
        assert cfg.reflection_enabled is True
        assert cfg.health_check_enabled is True
        assert cfg.address == "0.0.0.0:50051"

    def test_custom_values(self):
        cfg = GrpcServiceConfig(host="127.0.0.1", port=9090, max_workers=20)
        assert cfg.address == "127.0.0.1:9090"
        assert cfg.max_workers == 20

    def test_frozen(self):
        cfg = GrpcServiceConfig()
        with pytest.raises(AttributeError):
            cfg.port = 8080  # type: ignore[misc]

    def test_max_message_length_default(self):
        cfg = GrpcServiceConfig()
        assert cfg.max_message_length == 4 * 1024 * 1024
