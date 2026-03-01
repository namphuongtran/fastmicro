"""User domain entity - re-exported from shared library.

Canonical definitions live in ``shared.identity.entities.user``.
"""

from shared.identity.entities.user import (  # noqa: F401
    User,
    UserClaim,
    UserCredential,
    UserProfile,
    UserRole,
)

__all__ = [
    "User",
    "UserClaim",
    "UserCredential",
    "UserProfile",
    "UserRole",
]
