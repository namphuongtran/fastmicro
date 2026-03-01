"""PostgreSQL repository implementations for the identity platform.

These repositories implement the abstract interfaces defined in
identity-service/domain/repositories/ using SQLAlchemy async and
the shared ORM models.
"""

from shared.identity.repositories.client_repository import ClientRepository
from shared.identity.repositories.consent_repository import ConsentRepository
from shared.identity.repositories.password_reset_repository import PasswordResetRepository
from shared.identity.repositories.token_repository import RefreshTokenRepository
from shared.identity.repositories.user_repository import UserRepository

__all__ = [
    "ClientRepository",
    "ConsentRepository",
    "PasswordResetRepository",
    "RefreshTokenRepository",
    "UserRepository",
]
