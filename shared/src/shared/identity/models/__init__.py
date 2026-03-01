"""Identity ORM models package.

SQLAlchemy ORM models for the identity platform database (identity_db).
These models map to the domain entities defined in identity-service but
are located in the shared library so that both identity-service and
identity-admin-service can use the same persistence layer.

Tables:
    users, user_credentials, user_profiles, user_claims, user_roles,
    clients, client_secrets, client_scopes, client_redirect_uris,
    refresh_tokens, consents, consent_scopes, password_reset_tokens
"""

from shared.identity.models.base import IdentityBase
from shared.identity.models.client import (
    ClientModel,
    ClientRedirectUriModel,
    ClientScopeModel,
    ClientSecretModel,
)
from shared.identity.models.consent import ConsentModel, ConsentScopeModel
from shared.identity.models.token import RefreshTokenModel
from shared.identity.models.user import (
    PasswordResetTokenModel,
    UserClaimModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
    UserRoleModel,
)

__all__ = [
    "IdentityBase",
    # User aggregate
    "UserModel",
    "UserCredentialModel",
    "UserProfileModel",
    "UserClaimModel",
    "UserRoleModel",
    # Client aggregate
    "ClientModel",
    "ClientSecretModel",
    "ClientScopeModel",
    "ClientRedirectUriModel",
    # Token
    "RefreshTokenModel",
    # Consent
    "ConsentModel",
    "ConsentScopeModel",
    # Password reset
    "PasswordResetTokenModel",
]
