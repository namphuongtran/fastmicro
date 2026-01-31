"""Domain layer package."""

from identity_service.domain.entities import (
    AuthorizationCode,
    Client,
    ClientRedirectUri,
    ClientScope,
    ClientSecret,
    Consent,
    ConsentScope,
    RefreshToken,
    Session,
    TokenBlacklistEntry,
    TokenInfo,
    User,
    UserClaim,
    UserCredential,
    UserProfile,
    UserRole,
)
from identity_service.domain.repositories import (
    AuthorizationCodeRepository,
    ClientRepository,
    ConsentRepository,
    RefreshTokenRepository,
    SessionRepository,
    TokenBlacklistRepository,
    UserRepository,
)

__all__ = [
    # Entities
    "User",
    "UserCredential",
    "UserProfile",
    "UserClaim",
    "UserRole",
    "Client",
    "ClientSecret",
    "ClientScope",
    "ClientRedirectUri",
    "AuthorizationCode",
    "RefreshToken",
    "TokenInfo",
    "TokenBlacklistEntry",
    "Consent",
    "ConsentScope",
    "Session",
    # Repositories
    "UserRepository",
    "ClientRepository",
    "AuthorizationCodeRepository",
    "RefreshTokenRepository",
    "TokenBlacklistRepository",
    "ConsentRepository",
    "SessionRepository",
]
