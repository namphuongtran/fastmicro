"""gRPC & Protocol Buffers utilities.

This module provides helpers for building gRPC-based microservices:

* **ProtobufSerializer** – serialize / deserialize Pydantic models to/from
  ``google.protobuf.Struct`` and JSON transport format.
* **GrpcServiceConfig** – configuration dataclass for server/client settings.
* **grpc_status_to_http** / **http_status_to_grpc** – status code mapping.

.. note::
   Requires the ``grpc`` extras: ``pip install shared[grpc]``
"""

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

__all__ = [
    "GrpcServiceConfig",
    "ProtobufSerializer",
    "grpc_status_to_http",
    "http_status_to_grpc",
    "pydantic_to_struct",
    "struct_to_dict",
]