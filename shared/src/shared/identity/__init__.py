"""Shared identity module - ORM models, mappers, and repositories.

Provides the persistence layer for the identity platform, shared between
identity-service and identity-admin-service. Both services connect to the
same PostgreSQL database (identity_db).

Submodules:
    models: SQLAlchemy ORM models
    mappers: Entity <-> ORM model conversion
    repositories: PostgreSQL repository implementations
"""

__all__: list[str] = []
