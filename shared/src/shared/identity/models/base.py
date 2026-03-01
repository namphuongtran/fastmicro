"""Declarative base for identity platform models."""

from sqlalchemy.orm import DeclarativeBase


class IdentityBase(DeclarativeBase):
    """Base class for all identity platform ORM models.

    All identity ORM models derive from this base so that Alembic
    can discover them via ``IdentityBase.metadata``.
    """

    pass
