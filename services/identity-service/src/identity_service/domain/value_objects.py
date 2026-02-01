"""Domain value objects for Identity Service."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Self


class TokenType(StrEnum):
    """OAuth2 token types."""

    BEARER = "Bearer"
    MAC = "mac"


class GrantType(StrEnum):
    """OAuth2 grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    PASSWORD = "password"  # Legacy, not recommended
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"


class ResponseType(StrEnum):
    """OAuth2 response types."""

    CODE = "code"
    TOKEN = "token"  # Implicit, not recommended
    ID_TOKEN = "id_token"
    CODE_ID_TOKEN = "code id_token"


class ClientType(StrEnum):
    """OAuth2 client types."""

    CONFIDENTIAL = "confidential"  # Can securely store credentials
    PUBLIC = "public"  # Cannot store credentials (SPAs, mobile apps)


class AuthMethod(StrEnum):
    """Client authentication methods."""

    CLIENT_SECRET_BASIC = "client_secret_basic"
    CLIENT_SECRET_POST = "client_secret_post"
    CLIENT_SECRET_JWT = "client_secret_jwt"
    PRIVATE_KEY_JWT = "private_key_jwt"
    NONE = "none"  # For public clients


class Scope(StrEnum):
    """Standard OIDC scopes."""

    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    ADDRESS = "address"
    PHONE = "phone"
    OFFLINE_ACCESS = "offline_access"  # For refresh tokens


@dataclass(frozen=True)
class Email:
    """Email value object with validation."""

    value: str

    def __post_init__(self) -> None:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid email format: {self.value}")

    def __str__(self) -> str:
        return self.value

    @property
    def domain(self) -> str:
        """Get email domain."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Get email local part (before @)."""
        return self.value.split("@")[0]


@dataclass(frozen=True)
class Password:
    """Password value object with validation rules."""

    value: str

    @classmethod
    def validate(
        cls,
        value: str,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
    ) -> Self:
        """Validate password against policy and return instance."""
        errors: list[str] = []

        if len(value) < min_length:
            errors.append(f"Password must be at least {min_length} characters")

        if require_uppercase and not re.search(r"[A-Z]", value):
            errors.append("Password must contain at least one uppercase letter")

        if require_lowercase and not re.search(r"[a-z]", value):
            errors.append("Password must contain at least one lowercase letter")

        if require_digit and not re.search(r"\d", value):
            errors.append("Password must contain at least one digit")

        if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            errors.append("Password must contain at least one special character")

        if errors:
            raise ValueError("; ".join(errors))

        return cls(value=value)


@dataclass(frozen=True)
class RedirectUri:
    """Redirect URI value object with validation."""

    value: str

    def __post_init__(self) -> None:
        """Validate redirect URI format."""
        # Must be HTTPS in production (except localhost for development)
        if not self.value.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("Redirect URI must use HTTPS (except localhost)")

        # Must not contain fragments
        if "#" in self.value:
            raise ValueError("Redirect URI must not contain fragments")

    def __str__(self) -> str:
        return self.value

    def matches(self, uri: str) -> bool:
        """Check if given URI matches this redirect URI."""
        # Exact match for security
        return self.value == uri


@dataclass(frozen=True)
class ClientId:
    """Client ID value object."""

    value: str

    def __post_init__(self) -> None:
        """Validate client ID format."""
        if not self.value or len(self.value) < 8:
            raise ValueError("Client ID must be at least 8 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.value):
            raise ValueError("Client ID must contain only alphanumeric characters, underscores, and hyphens")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SubjectId:
    """Subject identifier value object (user ID in tokens)."""

    value: str

    def __post_init__(self) -> None:
        """Validate subject ID format."""
        if not self.value:
            raise ValueError("Subject ID cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CodeChallenge:
    """PKCE code challenge value object."""

    value: str
    method: str  # "S256" or "plain"

    def __post_init__(self) -> None:
        """Validate code challenge."""
        if self.method not in ("S256", "plain"):
            raise ValueError("Code challenge method must be 'S256' or 'plain'")
        if self.method == "plain":
            # plain method not recommended
            import warnings
            warnings.warn("Plain code challenge method is not recommended", UserWarning)
        if len(self.value) < 43 or len(self.value) > 128:
            raise ValueError("Code challenge must be between 43 and 128 characters")
