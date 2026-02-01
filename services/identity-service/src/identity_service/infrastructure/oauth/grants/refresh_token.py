"""Refresh Token Grant implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from authlib.oauth2.rfc6749 import grants

if TYPE_CHECKING:
    from identity_service.domain.entities import RefreshToken, User


class RefreshTokenGrant(grants.RefreshTokenGrant):
    """Refresh Token Grant for obtaining new access tokens.

    Implements RFC 6749 Section 6.
    Supports token rotation for enhanced security.
    """

    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        "none",  # For public clients
    ]

    # Scopes that can be renewed without re-consent
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token: str) -> RefreshToken | None:
        """Validate and return the refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            RefreshToken entity if valid.
        """
        token = self.server.query_refresh_token(refresh_token)
        if token and token.is_valid():
            return token
        return None

    def authenticate_user(self, credential: RefreshToken) -> User | None:
        """Get user associated with refresh token.

        Args:
            credential: Refresh token entity

        Returns:
            User entity if found.
        """
        if credential.user_id:
            return self.server.query_user(credential.user_id)
        return None

    def revoke_old_credential(self, credential: RefreshToken) -> None:
        """Revoke the old refresh token (token rotation).

        Args:
            credential: Old refresh token to revoke
        """
        self.server.revoke_refresh_token(credential.token)
