"""Health check and observability endpoints for Identity Admin Service.

Uses shared library's health router with database connectivity checks.
"""

from shared.fastapi_utils import create_database_health_check, create_health_router


async def _check_identity_db() -> bool:
    """Check identity database connectivity."""
    try:
        from identity_admin_service.database import get_db_manager

        return await get_db_manager().health_check()
    except Exception:
        return False


def register_health_checks() -> None:
    """Register health checks during application startup.

    Called from the app lifespan handler rather than at module import
    so tests can control when (and if) checks are registered.
    """
    create_database_health_check(
        name="identity_db",
        check_fn=_check_identity_db,
    )


# Create the shared health router (stateless - safe at module level)
router = create_health_router(
    service_name="identity-admin-service",
)
