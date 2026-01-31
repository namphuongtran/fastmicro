"""Domain entities package."""

from identity_service.domain.entities.client import (
    Client,
    ClientRedirectUri,
    ClientScope,
    ClientSecret,
)
from identity_service.domain.entities.consent import Consent, ConsentScope, Session
from identity_service.domain.entities.token import (
    AuthorizationCode,
    RefreshToken,
    TokenBlacklistEntry,
    TokenInfo,
)
from identity_service.domain.entities.user import (
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
    # Consent entities
    "Consent",
    "ConsentScope",
    "Session",
]
