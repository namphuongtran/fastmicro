"""Application layer service patterns.

This module provides base service patterns for the application layer:
- BaseService: Generic service with caching support
- BaseReadService: Read-only operations with caching
- BaseWriteService: Write operations with validation
- CRUDService: Combined read/write service
"""

from shared.application.base_service import (
    BaseReadService,
    BaseService,
    BaseWriteService,
    ConflictError,
    CRUDService,
    NotFoundError,
    ServiceContext,
    ServiceError,
    ValidationError,
)

__all__ = [
    "BaseReadService",
    "BaseService",
    "BaseWriteService",
    "CRUDService",
    "ConflictError",
    "NotFoundError",
    "ServiceContext",
    "ServiceError",
    "ValidationError",
]
