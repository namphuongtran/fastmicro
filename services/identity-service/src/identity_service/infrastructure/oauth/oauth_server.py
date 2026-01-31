"""Authlib OAuth2 Authorization Server implementation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Callable

from authlib.integrations.starlette_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6750 import BearerTokenGenerator
from authlib.oauth2.rfc7636 import CodeChallenge

from identity_service.infrastructure.oauth.grants import (
    AuthorizationCodeGrant,
    ClientCredentialsGrant,
    OpenIDCode,
    RefreshTokenGrant,
)

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings
    from identity_service.domain.entities import (
        AuthorizationCode,
        Client,
        RefreshToken,
        User,
    )
    from identity_service.infrastructure.security import JWTService, KeyManager


class AuthlibClient(ClientMixin):
    """Authlib-compatible client wrapper.

    Wraps our domain Client entity to implement Authlib's ClientMixin interface.
    """

    def __init__(self, client: Client) -> None:
        """Initialize wrapper.

        Args:
            client: Domain Client entity
        """
        self._client = client

    @property
    def client_id(self) -> str:
        """Get OAuth2 client_id."""
        return self._client.client_id

    def get_client_id(self) -> str:
        """Get OAuth2 client_id (Authlib interface)."""
        return self._client.client_id

    def get_default_redirect_uri(self) -> str | None:
        """Get default redirect URI."""
        default_uris = [r for r in self._client.redirect_uris if r.is_default]
        if default_uris:
            return default_uris[0].uri
        if self._client.redirect_uris:
            return self._client.redirect_uris[0].uri
        return None

    def get_allowed_scope(self, scope: str) -> str:
        """Filter scope to allowed values.

        Args:
            scope: Requested scope string

        Returns:
            Space-separated string of allowed scopes.
        """
        valid_scopes = self._client.validate_scope(scope)
        return " ".join(valid_scopes)

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate redirect URI.

        Args:
            redirect_uri: URI to validate

        Returns:
            True if URI is registered for this client.
        """
        return self._client.validate_redirect_uri(redirect_uri) is not None

    def check_client_secret(self, client_secret: str) -> bool:
        """Verify client secret.

        Args:
            client_secret: Secret to verify

        Returns:
            True if secret is valid.
        """
        return self._client.verify_secret(client_secret)

    def check_endpoint_auth_method(self, method: str, endpoint: str) -> bool:
        """Check if auth method is allowed for endpoint.

        Args:
            method: Authentication method
            endpoint: Endpoint name

        Returns:
            True if method is allowed.
        """
        if endpoint == "token":
            return method == self._client.token_endpoint_auth_method.value
        return True

    def check_response_type(self, response_type: str) -> bool:
        """Check if response type is supported.

        Args:
            response_type: Response type to check

        Returns:
            True if supported.
        """
        return self._client.supports_response_type(response_type)

    def check_grant_type(self, grant_type: str) -> bool:
        """Check if grant type is supported.

        Args:
            grant_type: Grant type to check

        Returns:
            True if supported.
        """
        return self._client.supports_grant(grant_type)

    @property
    def client(self) -> Client:
        """Get underlying domain client."""
        return self._client


class IdentityAuthorizationServer(AuthorizationServer):
    """Custom Authorization Server for Identity Service.

    Extends Authlib's AuthorizationServer with custom token generation
    and callback functions.
    """

    def __init__(
        self,
        settings: Settings,
        jwt_service: JWTService,
        key_manager: KeyManager,
    ) -> None:
        """Initialize authorization server.

        Args:
            settings: Application settings
            jwt_service: JWT service for token generation
            key_manager: RSA key manager
        """
        super().__init__()
        self._settings = settings
        self._jwt_service = jwt_service
        self._key_manager = key_manager

        # Callbacks set by application layer
        self._query_client: Callable[[str], Client | None] | None = None
        self._query_user: Callable[[uuid.UUID], User | None] | None = None
        self._save_token: Callable[[dict, Any], None] | None = None
        self._save_authorization_code: Callable[[AuthorizationCode], None] | None = None
        self._query_authorization_code: Callable[[str], AuthorizationCode | None] | None = None
        self._delete_authorization_code: Callable[[str], None] | None = None
        self._query_refresh_token: Callable[[str], RefreshToken | None] | None = None
        self._revoke_refresh_token: Callable[[str], None] | None = None

        # Register grants
        self._register_grants()

    def _register_grants(self) -> None:
        """Register supported OAuth2 grants."""
        # Authorization Code with PKCE and OpenID Connect
        self.register_grant(
            AuthorizationCodeGrant,
            [CodeChallenge(required=True), OpenIDCode(require_nonce=False)],
        )

        # Client Credentials
        self.register_grant(ClientCredentialsGrant)

        # Refresh Token
        self.register_grant(RefreshTokenGrant)

    def set_callbacks(
        self,
        query_client: Callable[[str], Client | None],
        query_user: Callable[[uuid.UUID], User | None],
        save_token: Callable[[dict, Any], None],
        save_authorization_code: Callable[[AuthorizationCode], None],
        query_authorization_code: Callable[[str], AuthorizationCode | None],
        delete_authorization_code: Callable[[str], None],
        query_refresh_token: Callable[[str], RefreshToken | None],
        revoke_refresh_token: Callable[[str], None],
    ) -> None:
        """Set callback functions for OAuth2 operations.

        Args:
            query_client: Function to get client by client_id
            query_user: Function to get user by user_id
            save_token: Function to save issued tokens
            save_authorization_code: Function to save auth codes
            query_authorization_code: Function to get auth codes
            delete_authorization_code: Function to delete auth codes
            query_refresh_token: Function to get refresh tokens
            revoke_refresh_token: Function to revoke refresh tokens
        """
        self._query_client = query_client
        self._query_user = query_user
        self._save_token = save_token
        self._save_authorization_code = save_authorization_code
        self._query_authorization_code = query_authorization_code
        self._delete_authorization_code = delete_authorization_code
        self._query_refresh_token = query_refresh_token
        self._revoke_refresh_token = revoke_refresh_token

    def query_client(self, client_id: str) -> AuthlibClient | None:
        """Query client by client_id (Authlib callback).

        Args:
            client_id: OAuth2 client_id

        Returns:
            Authlib-compatible client wrapper.
        """
        if not self._query_client:
            raise RuntimeError("query_client callback not set")

        client = self._query_client(client_id)
        if client:
            return AuthlibClient(client)
        return None

    def query_user(self, user_id: uuid.UUID) -> User | None:
        """Query user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User entity if found.
        """
        if not self._query_user:
            raise RuntimeError("query_user callback not set")
        return self._query_user(user_id)

    def save_token(self, token: dict, request: Any) -> None:
        """Save issued token (Authlib callback).

        Args:
            token: Token data dictionary
            request: OAuth2 request
        """
        if not self._save_token:
            raise RuntimeError("save_token callback not set")
        self._save_token(token, request)

    def save_authorization_code(self, code: AuthorizationCode) -> None:
        """Save authorization code.

        Args:
            code: Authorization code entity
        """
        if not self._save_authorization_code:
            raise RuntimeError("save_authorization_code callback not set")
        self._save_authorization_code(code)

    def query_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Query authorization code.

        Args:
            code: Authorization code string

        Returns:
            Authorization code if found.
        """
        if not self._query_authorization_code:
            raise RuntimeError("query_authorization_code callback not set")
        return self._query_authorization_code(code)

    def delete_authorization_code(self, code: str) -> None:
        """Delete authorization code.

        Args:
            code: Authorization code string
        """
        if not self._delete_authorization_code:
            raise RuntimeError("delete_authorization_code callback not set")
        self._delete_authorization_code(code)

    def query_refresh_token(self, token: str) -> RefreshToken | None:
        """Query refresh token.

        Args:
            token: Refresh token string

        Returns:
            RefreshToken if found.
        """
        if not self._query_refresh_token:
            raise RuntimeError("query_refresh_token callback not set")
        return self._query_refresh_token(token)

    def revoke_refresh_token(self, token: str) -> None:
        """Revoke refresh token.

        Args:
            token: Refresh token string
        """
        if not self._revoke_refresh_token:
            raise RuntimeError("revoke_refresh_token callback not set")
        self._revoke_refresh_token(token)

    def get_jwt_config(self) -> dict:
        """Get JWT configuration for ID token generation.

        Returns:
            JWT configuration dictionary.
        """
        return {
            "key": self._key_manager.private_key,
            "alg": self._settings.jwt_algorithm,
            "iss": self._settings.jwt_issuer,
            "exp": self._settings.id_token_lifetime,
        }

    def generate_token(
        self,
        client: AuthlibClient,
        grant_type: str,
        user: User | None = None,
        scope: str = "",
        include_refresh_token: bool = True,
        **kwargs: Any,
    ) -> dict:
        """Generate OAuth2 tokens.

        Args:
            client: OAuth2 client
            grant_type: Grant type used
            user: User entity (optional for client_credentials)
            scope: Granted scope
            include_refresh_token: Whether to include refresh token
            **kwargs: Additional parameters

        Returns:
            Token response dictionary.
        """
        subject = user.subject_id if user else client.client_id
        client_id = client.client_id

        # Generate access token
        access_token, jti, expires_in = self._jwt_service.create_access_token(
            subject=subject,
            client_id=client_id,
            scope=scope,
            expires_in=client.client.access_token_lifetime,
        )

        response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": scope,
        }

        # Include refresh token for user-based flows
        if include_refresh_token and user and "offline_access" in scope.split():
            from identity_service.domain.entities import RefreshToken

            refresh_token = RefreshToken(
                client_id=client_id,
                user_id=uuid.UUID(user.subject_id),
                scope=scope,
            )
            response["refresh_token"] = refresh_token.token

        # Include ID token for OpenID Connect
        if user and "openid" in scope.split():
            nonce = kwargs.get("nonce")
            id_token = self._jwt_service.create_id_token(
                subject=user.subject_id,
                client_id=client_id,
                nonce=nonce,
                claims=user.get_userinfo_claims(scope.split()),
                expires_in=client.client.id_token_lifetime,
            )
            response["id_token"] = id_token

        return response
