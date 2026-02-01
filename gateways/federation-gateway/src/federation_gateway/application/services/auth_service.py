"""
Authentication service for business logic
"""

import logging
from datetime import timedelta
from typing import Any

from fastapi import HTTPException

from federation_gateway.configs.settings import FederationGatewaySettings
from federation_gateway.domain.entities.auth_response import AuthenticationResult

from .token_service import TokenService

logger = logging.getLogger(__name__)


class AuthService:
    """Main authentication service."""

    def __init__(self, settings: FederationGatewaySettings, token_service: TokenService):
        self.settings = settings
        self.token_service = token_service

    def normalize_user_info(self, user_info: dict[str, Any]) -> dict[str, Any]:
        """Normalize user info from IdP."""
        return {
            "sub": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name", user_info.get("preferred_username", "")),
            "preferred_username": user_info.get("preferred_username"),
            "given_name": user_info.get("given_name"),
            "family_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
        }

    async def handle_successful_auth(self, token: dict[str, Any]) -> AuthenticationResult:
        """Handle successful authentication and create JWT."""
        try:
            # Get user info from IdP
            user_info = token.get("userinfo")
            if not user_info:
                logger.error("Failed to get user information from IdP token")
                return AuthenticationResult(
                    success=False,
                    error="server_error",
                    error_description="Failed to get user information",
                )

            # Normalize user info
            normalized_user_info = self.normalize_user_info(user_info)

            # Create access token
            access_token_expires = timedelta(minutes=self.settings.token_expire_minutes)
            access_token = self.token_service.create_access_token(
                data=normalized_user_info, expires_delta=access_token_expires
            )

            logger.info(f"Successfully authenticated user: {normalized_user_info.get('sub')}")

            return AuthenticationResult(success=True, access_token=access_token)

        except Exception as e:
            logger.error(f"Error handling successful authentication: {str(e)}")
            return AuthenticationResult(
                success=False,
                error="server_error",
                error_description="Authentication processing failed",
            )

    def validate_token_and_get_user_info(self, auth_header: str | None) -> dict[str, Any]:
        """Validate token and return user information."""
        token = self.token_service.extract_token_from_header(auth_header)
        payload = self.token_service.decode_token(token)
        return payload

    def logout_user(self, auth_header: str | None) -> bool:
        """Process user logout."""
        try:
            payload = self.validate_token_and_get_user_info(auth_header)
            logger.info(f"User logged out: {payload.get('sub')}")
            return True
        except HTTPException:
            return False
