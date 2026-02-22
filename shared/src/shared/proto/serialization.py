"""Protobuf ↔ Python serialization helpers.

Provides utilities for converting between Pydantic models, Python dicts,
and ``google.protobuf.Struct`` messages — useful for inter-service
communication over gRPC.

These helpers are deliberately lightweight so they can be used without
importing the full gRPC stack at module level.
"""

from __future__ import annotations

from typing import Any


class ProtobufSerializer:
    """Serialize / deserialize between Python dicts and Protobuf Struct.

    Example::

        serializer = ProtobufSerializer()
        struct_msg = serializer.dict_to_struct({"key": "value"})
        back = serializer.struct_to_dict(struct_msg)
    """

    @staticmethod
    def dict_to_struct(data: dict[str, Any]) -> Any:
        """Convert a Python dict to a ``google.protobuf.Struct``.

        Args:
            data: Python dictionary (JSON-serializable values).

        Returns:
            A ``google.protobuf.struct_pb2.Struct`` message.

        Raises:
            ImportError: If ``protobuf`` is not installed.
        """
        from google.protobuf.struct_pb2 import Struct

        struct = Struct()
        struct.update(data)
        return struct

    @staticmethod
    def struct_to_dict(struct: Any) -> dict[str, Any]:
        """Convert a ``google.protobuf.Struct`` to a Python dict.

        Args:
            struct: A ``Struct`` protobuf message.

        Returns:
            Plain Python dictionary.
        """
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(struct)


def pydantic_to_struct(model: Any) -> Any:
    """Convert a Pydantic model to a ``google.protobuf.Struct``.

    Uses ``model.model_dump(mode="json")`` for JSON-safe serialization.

    Args:
        model: A Pydantic v2 ``BaseModel`` instance.

    Returns:
        A ``google.protobuf.struct_pb2.Struct`` message.
    """
    data = model.model_dump(mode="json")
    return ProtobufSerializer.dict_to_struct(data)


def struct_to_dict(struct: Any) -> dict[str, Any]:
    """Convenience alias for ``ProtobufSerializer.struct_to_dict``."""
    return ProtobufSerializer.struct_to_dict(struct)


__all__ = [
    "ProtobufSerializer",
    "pydantic_to_struct",
    "struct_to_dict",
]
