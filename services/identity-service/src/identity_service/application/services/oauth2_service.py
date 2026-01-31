"""OAuth2 Application Service - orchestrates OAuth2/OIDC operations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from identity_service.application.dtos import (
    AuthorizationCodeResult,
    AuthorizationValidationResult,
    TokenResult,
    UserInfoResult,
)
from identity_service.domain.entities import (
    AuthorizationCode,
    RefreshToken,
    TokenInfo,
)

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings
    from identity_service.domain.entities import Client, User
    from identity_service.domain.repositories import (
        AuthorizationCodeRepository,
        ClientRepository,
        ConsentRepository,
        RefreshTokenRepository,
        SessionRepository,
        TokenBlacklistRepository,
        UserRepository,
    )
    from identity_service.infrastructure.security import JWTService, PasswordService


class OAuth2Service:
    """Application service for OAuth2/OIDC operations.

    Orchestrates domain entities and infrastructure services
    to implement OAuth2/OIDC flows.
    """

    def __init__(
        self,
        settings: Settings,
        jwt_service: JWTService,
        password_service: PasswordService,
        user_repository: UserRepository,
        client_repository: ClientRepository,
        auth_code_repository: AuthorizationCodeRepository,
        refresh_token_repository: RefreshTokenRepository,
        token_blacklist_repository: TokenBlacklistRepository,
        consent_repository: ConsentRepository,
        session_repository: SessionRepository,
    ) -> None:
        """Initialize OAuth2 service.

        Args:
            settings: Application settings
            jwt_service: JWT token service
            password_service: Password hashing service
            user_repository: User data access
            client_repository: Client data access
            auth_code_repository: Authorization code storage
            refresh_token_repository: Refresh token storage
            token_blacklist_repository: Token blacklist storage
            consent_repository: Consent storage
            session_repository: Session storage
        """
        self._settings = settings
        self._jwt_service = jwt_service
        self._password_service = password_service
        self._user_repo = user_repository
        self._client_repo = client_repository
        self._auth_code_repo = auth_code_repository
        self._refresh_token_repo = refresh_token_repository
        self._blacklist_repo = token_blacklist_repository
        self._consent_repo = consent_repository
        self._session_repo = session_repository

    async def validate_authorization_request(
        self,
        client_id: str,
        redirect_uri: str | None,
        response_type: str,
        scope: str | None,
    ) -> AuthorizationValidationResult:
        """Validate an authorization request.

        Args:
            client_id: OAuth2 client identifier
            redirect_uri: Requested redirect URI
            response_type: Requested response type
            scope: Requested scope

        Returns:
            Validation result with error or validated parameters.
        """
        # Get client
        client = await self._client_repo.get_by_client_id(client_id)
        if not client:
            return AuthorizationValidationResult(
                is_error=True,
                error="invalid_client",
                error_description="Client not found",
            )

        if not client.is_active:
            return AuthorizationValidationResult(
                is_error=True,
                error="invalid_client",
                error_description="Client is not active",
            )

        # Validate redirect URI
        validated_redirect = client.validate_redirect_uri(redirect_uri)
        if not validated_redirect:
            return AuthorizationValidationResult(
                is_error=True,
                error="invalid_request",
                error_description="Invalid redirect_uri",
            )

        # Validate response type
        if not client.supports_response_type(response_type):
            return AuthorizationValidationResult(
                is_error=True,
                error="unsupported_response_type",
                error_description=f"Response type '{response_type}' not supported",
                redirect_uri=validated_redirect,
            )

        # Validate and filter scope
        valid_scopes = client.validate_scope(scope or "")
        if not valid_scopes and scope:
            # If scope was requested but none valid, error
            return AuthorizationValidationResult(
                is_error=True,
                error="invalid_scope",
                error_description="No valid scopes requested",
                redirect_uri=validated_redirect,
            )

        return AuthorizationValidationResult(
            is_error=False,
            redirect_uri=validated_redirect,
            client_name=client.client_name,
            scopes=valid_scopes,
        )

    async def create_authorization_code(
        self,
        user_id: uuid.UUID,
        client_id: str,
        redirect_uri: str,
        scope: str | None,
        nonce: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> AuthorizationCodeResult:
        """Create an authorization code.

        Args:
            user_id: Authenticated user's ID
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI
            scope: Granted scope
            nonce: OIDC nonce
            code_challenge: PKCE challenge
            code_challenge_method: PKCE method

        Returns:
            Authorization code result.
        """
        auth_code = AuthorizationCode(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope or "",
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        await self._auth_code_repo.save(auth_code)

        return AuthorizationCodeResult(code=auth_code.code)

    async def exchange_code(
        self,
        code: str,
        client_id: str | None,
        client_secret: str | None,
        redirect_uri: str | None,
        code_verifier: str | None,
    ) -> TokenResult:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code
            client_id: Client identifier
            client_secret: Client secret
            redirect_uri: Original redirect URI
            code_verifier: PKCE verifier

        Returns:
            Token result with access/refresh/ID tokens.
        """
        # Get authorization code
        auth_code = await self._auth_code_repo.get_by_code(code)
        if not auth_code:
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="Invalid or expired authorization code",
            )

        if auth_code.is_used:
            # Code reuse attack - revoke all tokens for this code
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="Authorization code already used",
            )

        # Verify client
        client = await self._client_repo.get_by_client_id(auth_code.client_id)
        if not client:
            return TokenResult(
                is_error=True,
                error="invalid_client",
                error_description="Client not found",
            )

        # Verify client authentication for confidential clients
        if not client.is_public_client():
            if not client_secret or not client.verify_secret(client_secret):
                return TokenResult(
                    is_error=True,
                    error="invalid_client",
                    error_description="Invalid client credentials",
                )

        # Verify redirect URI matches
        if redirect_uri and redirect_uri != auth_code.redirect_uri:
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="Redirect URI mismatch",
            )

        # Verify PKCE
        if auth_code.code_challenge:
            if not code_verifier:
                return TokenResult(
                    is_error=True,
                    error="invalid_grant",
                    error_description="Code verifier required",
                )
            if not auth_code.verify_pkce(code_verifier):
                return TokenResult(
                    is_error=True,
                    error="invalid_grant",
                    error_description="Invalid code verifier",
                )

        # Mark code as used
        await self._auth_code_repo.mark_as_used(code)

        # Get user
        user = await self._user_repo.get_by_id(auth_code.user_id) if auth_code.user_id else None
        if not user:
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="User not found",
            )

        # Generate tokens
        return await self._generate_tokens(
            user=user,
            client=client,
            scope=auth_code.scope,
            nonce=auth_code.nonce,
        )

    async def client_credentials(
        self,
        client_id: str,
        client_secret: str,
        scope: str | None,
    ) -> TokenResult:
        """Issue tokens using client credentials grant.

        Args:
            client_id: Client identifier
            client_secret: Client secret
            scope: Requested scope

        Returns:
            Token result with access token.
        """
        client = await self._client_repo.get_by_client_id(client_id)
        if not client:
            return TokenResult(
                is_error=True,
                error="invalid_client",
                error_description="Client not found",
            )

        if not client.verify_secret(client_secret):
            return TokenResult(
                is_error=True,
                error="invalid_client",
                error_description="Invalid client credentials",
            )

        if not client.supports_grant("client_credentials"):
            return TokenResult(
                is_error=True,
                error="unauthorized_client",
                error_description="Client not authorized for client_credentials grant",
            )

        # Filter scope
        valid_scope = " ".join(client.validate_scope(scope or ""))

        # Generate access token (no refresh token for client credentials)
        access_token, jti, expires_in = self._jwt_service.create_access_token(
            subject=client_id,
            client_id=client_id,
            scope=valid_scope,
            expires_in=client.access_token_lifetime,
        )

        return TokenResult(
            access_token=access_token,
            expires_in=expires_in,
            scope=valid_scope,
        )

    async def refresh_token(
        self,
        refresh_token: str,
        client_id: str | None,
        client_secret: str | None,
        scope: str | None,
    ) -> TokenResult:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token
            client_id: Client identifier
            client_secret: Client secret
            scope: Requested scope (must be subset of original)

        Returns:
            Token result with new tokens.
        """
        # Get refresh token
        token = await self._refresh_token_repo.get_by_token(refresh_token)
        if not token or not token.is_valid():
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="Invalid or expired refresh token",
            )

        # Verify client
        client = await self._client_repo.get_by_client_id(token.client_id)
        if not client:
            return TokenResult(
                is_error=True,
                error="invalid_client",
                error_description="Client not found",
            )

        # Verify client authentication for confidential clients
        if not client.is_public_client():
            if not client_secret or not client.verify_secret(client_secret):
                return TokenResult(
                    is_error=True,
                    error="invalid_client",
                    error_description="Invalid client credentials",
                )

        # Get user
        user = await self._user_repo.get_by_id(token.user_id) if token.user_id else None
        if not user:
            return TokenResult(
                is_error=True,
                error="invalid_grant",
                error_description="User not found",
            )

        # Validate scope (must be subset of original)
        original_scopes = set(token.scope.split())
        requested_scopes = set(scope.split()) if scope else original_scopes
        if not requested_scopes.issubset(original_scopes):
            return TokenResult(
                is_error=True,
                error="invalid_scope",
                error_description="Requested scope exceeds original grant",
            )

        # Revoke old token (token rotation)
        new_tokens = await self._generate_tokens(
            user=user,
            client=client,
            scope=" ".join(requested_scopes),
        )

        # Revoke old refresh token
        await self._refresh_token_repo.revoke(
            refresh_token,
            replaced_by=new_tokens.refresh_token,
        )

        return new_tokens

    async def _generate_tokens(
        self,
        user: User,
        client: Client,
        scope: str,
        nonce: str | None = None,
    ) -> TokenResult:
        """Generate access, refresh, and ID tokens.

        Args:
            user: User entity
            client: Client entity
            scope: Granted scope
            nonce: OIDC nonce

        Returns:
            Token result.
        """
        scopes = scope.split() if scope else []

        # Generate access token
        access_token, jti, expires_in = self._jwt_service.create_access_token(
            subject=user.subject_id,
            client_id=client.client_id,
            scope=scope,
            claims={"roles": user.get_active_roles()} if user.roles else None,
            expires_in=client.access_token_lifetime,
        )

        result = TokenResult(
            access_token=access_token,
            expires_in=expires_in,
            scope=scope,
        )

        # Generate refresh token if offline_access scope granted
        if "offline_access" in scopes:
            refresh_token = RefreshToken(
                client_id=client.client_id,
                user_id=user.id,
                scope=scope,
            )
            await self._refresh_token_repo.save(refresh_token)
            result.refresh_token = refresh_token.token

        # Generate ID token if openid scope granted
        if "openid" in scopes:
            result.id_token = self._jwt_service.create_id_token(
                subject=user.subject_id,
                client_id=client.client_id,
                nonce=nonce,
                claims=user.get_userinfo_claims(scopes),
                expires_in=client.id_token_lifetime,
            )

        return result

    async def verify_client(self, client_id: str, client_secret: str) -> bool:
        """Verify client credentials.

        Args:
            client_id: Client identifier
            client_secret: Client secret

        Returns:
            True if credentials are valid.
        """
        client = await self._client_repo.get_by_client_id(client_id)
        if not client:
            return False
        return client.verify_secret(client_secret)

    async def introspect_token(
        self,
        token: str,
        token_type_hint: str | None = None,
    ) -> TokenInfo:
        """Introspect a token.

        Args:
            token: Token to introspect
            token_type_hint: Hint about token type

        Returns:
            Token information.
        """
        # Try to decode as JWT (access token)
        claims = self._jwt_service.decode_token(token)
        if claims:
            # Check if blacklisted
            jti = claims.get("jti")
            if jti and await self._blacklist_repo.is_blacklisted(jti):
                return TokenInfo(active=False)

            return TokenInfo(
                active=True,
                scope=claims.get("scope"),
                client_id=claims.get("client_id"),
                sub=claims.get("sub"),
                exp=claims.get("exp"),
                iat=claims.get("iat"),
                nbf=claims.get("nbf"),
                iss=claims.get("iss"),
                aud=claims.get("aud"),
                jti=jti,
            )

        # Try as refresh token
        refresh = await self._refresh_token_repo.get_by_token(token)
        if refresh and refresh.is_valid():
            return TokenInfo(
                active=True,
                scope=refresh.scope,
                client_id=refresh.client_id,
                sub=str(refresh.user_id) if refresh.user_id else None,
                exp=int(refresh.expires_at.timestamp()) if refresh.expires_at else None,
                iat=int(refresh.issued_at.timestamp()),
            )

        return TokenInfo(active=False)

    async def revoke_token(
        self,
        token: str,
        client_id: str,
        token_type_hint: str | None = None,
    ) -> None:
        """Revoke a token.

        Args:
            token: Token to revoke
            client_id: Client that owns the token
            token_type_hint: Hint about token type
        """
        from datetime import datetime

        from identity_service.domain.entities import TokenBlacklistEntry

        # Try as JWT access token
        claims = self._jwt_service.decode_token(token, verify=False)
        if claims:
            jti = claims.get("jti")
            exp = claims.get("exp")
            if jti:
                entry = TokenBlacklistEntry(
                    jti=jti,
                    reason="client_revocation",
                    expires_at=datetime.fromtimestamp(exp) if exp else None,
                )
                await self._blacklist_repo.add(entry)

        # Try as refresh token
        await self._refresh_token_repo.revoke(token)

    async def get_userinfo(self, access_token: str) -> UserInfoResult:
        """Get user info from access token.

        Args:
            access_token: Bearer access token

        Returns:
            User info result with claims.
        """
        # Decode and validate token
        claims = self._jwt_service.decode_token(access_token)
        if not claims:
            return UserInfoResult(
                is_error=True,
                error="invalid_token",
                error_description="Token is invalid or expired",
            )

        # Check blacklist
        jti = claims.get("jti")
        if jti and await self._blacklist_repo.is_blacklisted(jti):
            return UserInfoResult(
                is_error=True,
                error="invalid_token",
                error_description="Token has been revoked",
            )

        # Get user
        user_id = claims.get("sub")
        if not user_id:
            return UserInfoResult(
                is_error=True,
                error="invalid_token",
                error_description="Token missing subject",
            )

        user = await self._user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            return UserInfoResult(
                is_error=True,
                error="invalid_token",
                error_description="User not found",
            )

        # Get scopes from token
        scope = claims.get("scope", "")
        scopes = scope.split() if scope else []

        return UserInfoResult(claims=user.get_userinfo_claims(scopes))

    async def get_user_from_session(self, session_id: str) -> User | None:
        """Get user from session.

        Args:
            session_id: Session identifier

        Returns:
            User if session is valid.
        """
        try:
            session = await self._session_repo.get_by_id(uuid.UUID(session_id))
            if session and session.is_valid() and session.user_id:
                return await self._user_repo.get_by_id(session.user_id)
        except ValueError:
            pass
        return None

    async def needs_consent(
        self,
        user_id: uuid.UUID,
        client_id: str,
        scope: str | None,
    ) -> bool:
        """Check if user needs to grant consent.

        Args:
            user_id: User identifier
            client_id: Client identifier
            scope: Requested scope

        Returns:
            True if consent is needed.
        """
        # Get client
        client = await self._client_repo.get_by_client_id(client_id)
        if not client:
            return True

        # First-party clients may skip consent
        if client.is_first_party:
            return False

        # Check existing consent
        consent = await self._consent_repo.get_by_user_and_client(user_id, client_id)
        if not consent or not consent.is_valid():
            return True

        # Check if all requested scopes are covered
        requested_scopes = scope.split() if scope else []
        return not consent.covers_scopes(requested_scopes)
