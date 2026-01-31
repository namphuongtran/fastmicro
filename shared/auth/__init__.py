"""Authentication and security utilities for microservices.

This module provides enterprise-grade authentication services:

- **JWT Management**: Token creation, verification, and validation
- **Password Hashing**: Argon2-based secure password handling
- **API Keys**: Generation and validation for service authentication

Example:
    >>> from shared.auth import JWTService, PasswordService, APIKeyService
    
    # JWT tokens
    >>> jwt = JWTService(secret_key="secret")
    >>> token = jwt.create_access_token("user_123", scopes=["read"])
    >>> data = jwt.verify_token(token)
    >>> print(data.sub)
    'user_123'
    
    # Password hashing
    >>> pwd = PasswordService()
    >>> hashed = pwd.hash("SecureP@ssw0rd!")
    >>> pwd.verify("SecureP@ssw0rd!", hashed)
    True
    
    # API keys
    >>> api = APIKeyService(prefix="sk_test_")
    >>> key = api.generate_key()
    >>> api.verify_key(key, api.hash_key(key))
    True

Security Best Practices:
    - Store JWT secret keys securely (env vars, secret managers)
    - Use appropriate token expiration times
    - Validate all tokens on every request
    - Never store plain-text passwords
    - Rehash passwords when security parameters change
    - Use unique prefixes for different API key types
"""

from shared.auth.api_key import (
    APIKeyData,
    APIKeyService,
    InvalidAPIKeyError,
)
from shared.auth.jwt import (
    ExpiredTokenError,
    InvalidTokenError,
    JWTService,
    TokenData,
    TokenType,
)
from shared.auth.password import (
    PasswordService,
    PasswordStrengthError,
    check_password_strength,
)

__all__ = [
    # JWT
    "JWTService",
    "TokenData",
    "TokenType",
    "InvalidTokenError",
    "ExpiredTokenError",
    # Password
    "PasswordService",
    "PasswordStrengthError",
    "check_password_strength",
    # API Key
    "APIKeyService",
    "APIKeyData",
    "InvalidAPIKeyError",
]
