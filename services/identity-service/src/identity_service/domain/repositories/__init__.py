"""Domain repositories package."""

from identity_service.domain.repositories.client_repository import ClientRepository
from identity_service.domain.repositories.consent_repository import (
    ConsentRepository,
    SessionRepository,
)
from identity_service.domain.repositories.token_repository import (
    AuthorizationCodeRepository,
    RefreshTokenRepository,
    TokenBlacklistRepository,
)
from identity_service.domain.repositories.password_reset_repository import (
    PasswordResetRepository,
)
from identity_service.domain.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "ClientRepository",
    "AuthorizationCodeRepository",
    "RefreshTokenRepository",
    "TokenBlacklistRepository",
    "ConsentRepository",
    "SessionRepository",
    "PasswordResetRepository",
]
