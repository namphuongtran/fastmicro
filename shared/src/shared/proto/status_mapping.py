"""gRPC ↔ HTTP status code mapping and service configuration.

Provides bidirectional mapping between gRPC status codes and HTTP status
codes, plus a configuration dataclass for gRPC server/client settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# gRPC ↔ HTTP status mapping
# ---------------------------------------------------------------------------

# Maps gRPC status code integers to HTTP status codes.
# Reference: https://grpc.github.io/grpc/core/md_doc_statuscodes.html
_GRPC_TO_HTTP: dict[int, int] = {
    0: 200,   # OK → OK
    1: 499,   # CANCELLED → Client Closed Request
    2: 500,   # UNKNOWN → Internal Server Error
    3: 400,   # INVALID_ARGUMENT → Bad Request
    4: 504,   # DEADLINE_EXCEEDED → Gateway Timeout
    5: 404,   # NOT_FOUND → Not Found
    6: 409,   # ALREADY_EXISTS → Conflict
    7: 403,   # PERMISSION_DENIED → Forbidden
    8: 429,   # RESOURCE_EXHAUSTED → Too Many Requests
    9: 400,   # FAILED_PRECONDITION → Bad Request
    10: 409,  # ABORTED → Conflict
    11: 400,  # OUT_OF_RANGE → Bad Request
    12: 501,  # UNIMPLEMENTED → Not Implemented
    13: 500,  # INTERNAL → Internal Server Error
    14: 503,  # UNAVAILABLE → Service Unavailable
    15: 500,  # DATA_LOSS → Internal Server Error
    16: 401,  # UNAUTHENTICATED → Unauthorized
}

# Reverse: HTTP → gRPC (most common mappings)
_HTTP_TO_GRPC: dict[int, int] = {
    200: 0,   # OK
    400: 3,   # Bad Request → INVALID_ARGUMENT
    401: 16,  # Unauthorized → UNAUTHENTICATED
    403: 7,   # Forbidden → PERMISSION_DENIED
    404: 5,   # Not Found → NOT_FOUND
    409: 6,   # Conflict → ALREADY_EXISTS
    429: 8,   # Too Many Requests → RESOURCE_EXHAUSTED
    499: 1,   # Client Closed → CANCELLED
    500: 13,  # Internal → INTERNAL
    501: 12,  # Not Implemented → UNIMPLEMENTED
    503: 14,  # Service Unavailable → UNAVAILABLE
    504: 4,   # Gateway Timeout → DEADLINE_EXCEEDED
}


def grpc_status_to_http(grpc_code: int) -> int:
    """Map a gRPC status code to the corresponding HTTP status code.

    Args:
        grpc_code: gRPC status code (0-16).

    Returns:
        HTTP status code.

    Raises:
        ValueError: If the gRPC code is unknown.
    """
    if grpc_code not in _GRPC_TO_HTTP:
        raise ValueError(f"Unknown gRPC status code: {grpc_code}")
    return _GRPC_TO_HTTP[grpc_code]


def http_status_to_grpc(http_code: int) -> int:
    """Map an HTTP status code to the closest gRPC status code.

    Args:
        http_code: HTTP status code.

    Returns:
        gRPC status code.

    Raises:
        ValueError: If no mapping exists for the HTTP code.
    """
    if http_code not in _HTTP_TO_GRPC:
        raise ValueError(f"No gRPC mapping for HTTP status code: {http_code}")
    return _HTTP_TO_GRPC[http_code]


# ---------------------------------------------------------------------------
# Service configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrpcServiceConfig:
    """Configuration for a gRPC service.

    Attributes:
        host: Bind address for the server.
        port: Bind port for the server.
        max_workers: Thread pool size for the server.
        max_message_length: Maximum send/receive message size in bytes.
        reflection_enabled: Enable gRPC server reflection.
        health_check_enabled: Enable gRPC health checking protocol.
        interceptors: List of server interceptor class paths.
        options: Additional gRPC channel options.
    """

    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 10
    max_message_length: int = 4 * 1024 * 1024  # 4 MB
    reflection_enabled: bool = True
    health_check_enabled: bool = True
    interceptors: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        """Full bind address string."""
        return f"{self.host}:{self.port}"


__all__ = [
    "GrpcServiceConfig",
    "grpc_status_to_http",
    "http_status_to_grpc",
]
