"""
Token service for JWT operations
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException

from federation_gateway.configs.settings import FederationGatewaySettings


class TokenService:
    """Service for JWT token operations."""

    def __init__(self, settings: FederationGatewaySettings):
        self.settings = settings

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=self.settings.token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(UTC),
            "iss": "federation-gateway"
        })

        secret_key = self.settings.jwt_secret.get_secret_value()
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=self.settings.jwt_algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate JWT token."""
        try:
            secret_key = self.settings.jwt_secret.get_secret_value()
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def extract_token_from_header(self, auth_header: str | None) -> str:
        """Extract token from Authorization header."""
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        return auth_header.split(" ")[1]
