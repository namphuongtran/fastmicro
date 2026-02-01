"""Authlib OAuth2 server integration - Authorization Code Grant with PKCE."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from authlib.oauth2 import OAuth2Request
from authlib.oauth2.rfc6749 import grants
from authlib.oidc.core import OpenIDCode as BaseOpenIDCode

if TYPE_CHECKING:
    from identity_service.domain.entities import AuthorizationCode, User


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Authorization Code Grant with PKCE support.

    Implements RFC 6749 (OAuth 2.0) and RFC 7636 (PKCE).
    """

    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        "none",
    ]
    AUTHORIZATION_CODE_LENGTH = 48

    def save_authorization_code(self, code: str, request: OAuth2Request) -> Any:
        """Save the authorization code to storage.

        Args:
            code: Generated authorization code
            request: OAuth2 request containing client, user, scope, etc.

        Returns:
            Authorization code entity.
        """
        from identity_service.domain.entities import AuthorizationCode

        auth_code = AuthorizationCode(
            code=code,
            client_id=request.client.client_id,
            user_id=uuid.UUID(request.user.subject_id) if request.user else None,
            redirect_uri=request.redirect_uri,
            scope=request.scope or "",
            nonce=request.data.get("nonce"),
            state=request.data.get("state"),
            code_challenge=request.data.get("code_challenge"),
            code_challenge_method=request.data.get("code_challenge_method"),
        )

        # Save via server's save_authorization_code callback
        self.server.save_authorization_code(auth_code)
        return auth_code

    def query_authorization_code(
        self, code: str, client: Any
    ) -> AuthorizationCode | None:
        """Query authorization code from storage.

        Args:
            code: Authorization code string
            client: OAuth2 client

        Returns:
            Authorization code if found and valid.
        """
        auth_code = self.server.query_authorization_code(code)
        if auth_code and auth_code.client_id == client.client_id:
            return auth_code
        return None

    def delete_authorization_code(self, authorization_code: Any) -> None:
        """Delete authorization code after use.

        Args:
            authorization_code: Authorization code entity
        """
        self.server.delete_authorization_code(authorization_code.code)

    def authenticate_user(self, authorization_code: Any) -> User | None:
        """Get user from authorization code.

        Args:
            authorization_code: Authorization code entity

        Returns:
            User entity if found.
        """
        if authorization_code.user_id:
            return self.server.query_user(authorization_code.user_id)
        return None


class OpenIDCode(BaseOpenIDCode):
    """OpenID Connect extension for Authorization Code Grant.

    Adds ID token generation and nonce validation.
    """

    def exists_nonce(self, nonce: str, request: OAuth2Request) -> bool:
        """Check if nonce was already used.

        Args:
            nonce: Nonce value from request
            request: OAuth2 request

        Returns:
            True if nonce exists (already used).
        """
        # For MVP, we don't track nonces - production should implement
        return False

    def get_jwt_config(self, grant: grants.AuthorizationCodeGrant) -> dict:
        """Get JWT configuration for ID token.

        Args:
            grant: Authorization code grant instance

        Returns:
            JWT configuration dictionary.
        """
        return self.server.get_jwt_config()

    def generate_user_info(self, user: Any, scope: str) -> dict:
        """Generate userinfo claims for ID token.

        Args:
            user: User entity
            scope: Space-separated scope string

        Returns:
            Dictionary of user claims.
        """
        scopes = scope.split() if scope else []
        return user.get_userinfo_claims(scopes)
