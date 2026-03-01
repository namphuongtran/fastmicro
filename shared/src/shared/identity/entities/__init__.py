"""Shared identity domain entities.

These entities represent the core domain objects for the identity platform.
They are shared between identity-service and identity-admin-service.
"""

from shared.identity.entities.client import (
    Client,
    ClientRedirectUri,
    ClientScope,
    ClientSecret,
)
from shared.identity.entities.consent import Consent, ConsentScope, Session
from shared.identity.entities.password_reset import PasswordResetToken
from shared.identity.entities.token import (
    AuthorizationCode,
    RefreshToken,
    TokenBlacklistEntry,
    TokenInfo,
)
from shared.identity.entities.user import (
    User,
    UserClaim,
    UserCredential,
    UserProfile,
    UserRole,
)

__all__ = [
    # User aggregate
    "User",
    "UserCredential",
    "UserProfile",
    "UserClaim",
    "UserRole",
    # Client aggregate
    "Client",
    "ClientSecret",
    "ClientScope",
    "ClientRedirectUri",
    # Token entities
    "AuthorizationCode",
    "RefreshToken",
    "TokenInfo",
    "TokenBlacklistEntry",
    # Password reset
    "PasswordResetToken",
    # Consent entities
    "Consent",
    "ConsentScope",
    "Session",
]
