"""JWT token utilities - RSA key management and JWT operations."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings


class KeyManager:
    """RSA key manager for JWT signing and verification.

    Handles loading, generating, and rotating RSA key pairs.
    """

    def __init__(self, private_key_path: str, public_key_path: str) -> None:
        """Initialize key manager.

        Args:
            private_key_path: Path to RSA private key PEM file
            public_key_path: Path to RSA public key PEM file
        """
        self._private_key_path = Path(private_key_path)
        self._public_key_path = Path(public_key_path)
        self._private_key: bytes | None = None
        self._public_key: bytes | None = None
        self._kid: str | None = None

    def load_or_generate_keys(self) -> None:
        """Load existing keys or generate new ones if not found."""
        if self._private_key_path.exists() and self._public_key_path.exists():
            self._load_keys()
        else:
            self._generate_keys()

    def _load_keys(self) -> None:
        """Load keys from files."""
        self._private_key = self._private_key_path.read_bytes()
        self._public_key = self._public_key_path.read_bytes()
        # Generate KID from public key hash
        import hashlib

        self._kid = hashlib.sha256(self._public_key).hexdigest()[:16]

    def _generate_keys(self) -> None:
        """Generate new RSA key pair."""
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Serialize private key
        self._private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key
        public_key = private_key.public_key()
        self._public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Ensure directories exist
        self._private_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._public_key_path.parent.mkdir(parents=True, exist_ok=True)

        # Write keys to files
        self._private_key_path.write_bytes(self._private_key)
        self._public_key_path.write_bytes(self._public_key)

        # Generate KID
        import hashlib

        self._kid = hashlib.sha256(self._public_key).hexdigest()[:16]

    @property
    def private_key(self) -> bytes:
        """Get private key bytes."""
        if self._private_key is None:
            self.load_or_generate_keys()
        return self._private_key  # type: ignore

    @property
    def public_key(self) -> bytes:
        """Get public key bytes."""
        if self._public_key is None:
            self.load_or_generate_keys()
        return self._public_key  # type: ignore

    @property
    def kid(self) -> str:
        """Get key ID."""
        if self._kid is None:
            self.load_or_generate_keys()
        return self._kid  # type: ignore

    def get_jwks(self) -> dict:
        """Get JSON Web Key Set (JWKS) for public key.

        Returns:
            JWKS dictionary with public key in JWK format.
        """
        from authlib.jose import JsonWebKey

        jwk = JsonWebKey.import_key(self.public_key, {"kty": "RSA"})
        jwk_dict = dict(jwk)
        jwk_dict["kid"] = self.kid
        jwk_dict["use"] = "sig"
        jwk_dict["alg"] = "RS256"

        return {"keys": [jwk_dict]}


class JWTService:
    """JWT token generation and validation service."""

    def __init__(self, settings: Settings, key_manager: KeyManager) -> None:
        """Initialize JWT service.

        Args:
            settings: Application settings
            key_manager: RSA key manager
        """
        self._settings = settings
        self._key_manager = key_manager

    def create_access_token(
        self,
        subject: str,
        client_id: str,
        scope: str,
        audience: str | list[str] | None = None,
        claims: dict | None = None,
        expires_in: int | None = None,
    ) -> tuple[str, str, int]:
        """Create a JWT access token.

        Args:
            subject: Subject identifier (user ID)
            client_id: OAuth2 client ID
            scope: Space-separated scope string
            audience: Token audience (defaults to issuer)
            claims: Additional claims to include
            expires_in: Token lifetime in seconds (overrides default)

        Returns:
            Tuple of (token, jti, expires_in).
        """
        from authlib.jose import jwt

        now = datetime.utcnow()
        lifetime = expires_in or self._settings.access_token_lifetime
        exp = now + timedelta(seconds=lifetime)
        jti = str(uuid.uuid4())

        payload = {
            "iss": self._settings.jwt_issuer,
            "sub": subject,
            "aud": audience or self._settings.jwt_audience,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": jti,
            "client_id": client_id,
            "scope": scope,
        }

        if claims:
            payload.update(claims)

        header = {
            "alg": self._settings.jwt_algorithm,
            "typ": "at+jwt",  # RFC 9068 access token type
            "kid": self._key_manager.kid,
        }

        token = jwt.encode(header, payload, self._key_manager.private_key)
        return token.decode("utf-8"), jti, lifetime

    def create_id_token(
        self,
        subject: str,
        client_id: str,
        nonce: str | None = None,
        auth_time: int | None = None,
        claims: dict | None = None,
        expires_in: int | None = None,
    ) -> str:
        """Create an OIDC ID token.

        Args:
            subject: Subject identifier (user ID)
            client_id: OAuth2 client ID (audience)
            nonce: Nonce from authorization request
            auth_time: Time of authentication
            claims: Additional claims to include
            expires_in: Token lifetime in seconds

        Returns:
            Encoded ID token.
        """
        from authlib.jose import jwt

        now = datetime.utcnow()
        lifetime = expires_in or self._settings.id_token_lifetime
        exp = now + timedelta(seconds=lifetime)

        payload = {
            "iss": self._settings.jwt_issuer,
            "sub": subject,
            "aud": client_id,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
        }

        if nonce:
            payload["nonce"] = nonce

        if auth_time:
            payload["auth_time"] = auth_time

        if claims:
            payload.update(claims)

        header = {
            "alg": self._settings.jwt_algorithm,
            "typ": "JWT",
            "kid": self._key_manager.kid,
        }

        token = jwt.encode(header, payload, self._key_manager.private_key)
        return token.decode("utf-8")

    def decode_token(self, token: str, verify: bool = True) -> dict | None:
        """Decode and optionally verify a JWT token.

        Args:
            token: JWT token string
            verify: Whether to verify signature

        Returns:
            Token claims if valid, None otherwise.
        """
        from authlib.jose import jwt
        from authlib.jose.errors import JoseError

        try:
            claims = jwt.decode(
                token,
                self._key_manager.public_key,
                claims_options={
                    "iss": {"essential": True, "value": self._settings.jwt_issuer},
                },
            )
            if verify:
                claims.validate()
            return dict(claims)
        except JoseError:
            return None

    def get_token_jti(self, token: str) -> str | None:
        """Extract JTI from token without verification.

        Args:
            token: JWT token string

        Returns:
            JTI if present, None otherwise.
        """
        claims = self.decode_token(token, verify=False)
        return claims.get("jti") if claims else None


@lru_cache
def get_key_manager(settings: Settings) -> KeyManager:
    """Get cached key manager instance."""
    manager = KeyManager(
        private_key_path=settings.jwt_private_key_path,
        public_key_path=settings.jwt_public_key_path,
    )
    manager.load_or_generate_keys()
    return manager


@lru_cache
def get_jwt_service(settings: Settings) -> JWTService:
    """Get cached JWT service instance."""
    return JWTService(settings, get_key_manager(settings))
