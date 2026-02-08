"""FastAPI dependency factories for service layer integration.

Provides injectable dependencies that bridge FastAPI's request handling
with the application layer's ServiceContext, enabling services to
access user identity, tenant, and correlation data.

Example:
    >>> from shared.fastapi_utils.dependencies import get_service_context
    >>> from shared.application import ServiceContext
    >>>
    >>> @router.post("/items")
    >>> async def create_item(
    ...     data: CreateItemDTO,
    ...     ctx: ServiceContext = Depends(get_service_context),
    ... ):
    ...     return await item_service.create(data, context=ctx)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from shared.application.base_service import ServiceContext
from shared.fastapi_utils.middleware import get_correlation_id, get_request_context


async def get_service_context(
    request: Request,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> ServiceContext:
    """FastAPI dependency that creates a ServiceContext from the current request.

    Extracts identity information from:
    1. JWT token claims (via request.state.user set by auth middleware)
    2. Request context middleware (correlation_id)
    3. Request headers (X-Tenant-ID)

    This dependency should be used in route handlers that invoke
    application-layer services requiring a ServiceContext.

    Args:
        request: The current FastAPI request.
        x_tenant_id: Optional tenant ID from request header.

    Returns:
        Populated ServiceContext for the current request.

    Example:
        >>> @router.get("/users/{user_id}")
        ... async def get_user(
        ...     user_id: str,
        ...     ctx: ServiceContext = Depends(get_service_context),
        ... ):
        ...     return await user_service.get_by_id(user_id, context=ctx)
    """
    # Extract user identity from JWT claims (set by auth middleware)
    user_id: str | None = None
    roles: list[str] = []
    permissions: list[str] = []

    # Check request.state for JWT-decoded user info
    user_state = getattr(request.state, "user", None)
    if user_state is not None:
        if isinstance(user_state, dict):
            user_id = user_state.get("sub") or user_state.get("user_id")
            roles = user_state.get("roles", [])
            permissions = user_state.get("permissions", [])
        else:
            # Support user objects with attributes
            user_id = getattr(user_state, "sub", None) or getattr(user_state, "user_id", None)
            roles = getattr(user_state, "roles", [])
            permissions = getattr(user_state, "permissions", [])

    # Get correlation ID from middleware context
    correlation_id = get_correlation_id()

    # Get tenant_id: prefer header, fallback to JWT claim
    tenant_id = x_tenant_id
    if tenant_id is None and user_state is not None:
        if isinstance(user_state, dict):
            tenant_id = user_state.get("tenant_id")
        else:
            tenant_id = getattr(user_state, "tenant_id", None)

    # Build metadata from request context
    metadata: dict[str, str] = {}
    req_ctx = get_request_context()
    if req_ctx is not None:
        metadata["request_id"] = req_ctx.request_id

    # Add client IP for audit purposes
    if request.client:
        metadata["client_ip"] = request.client.host

    return ServiceContext(
        user_id=user_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        roles=roles,
        permissions=permissions,
        metadata=metadata,
    )


# Annotated type for convenient dependency injection
ServiceContextDep = Annotated[ServiceContext, Depends(get_service_context)]
"""Annotated type alias for ServiceContext dependency injection.

Example:
    >>> @router.post("/items")
    ... async def create_item(
    ...     data: CreateItemDTO,
    ...     ctx: ServiceContextDep,
    ... ):
    ...     return await item_service.create(data, context=ctx)
"""
