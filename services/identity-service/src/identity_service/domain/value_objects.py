"""Domain value objects - re-exported from shared library.

Canonical definitions live in ``shared.identity.value_objects``.
"""

from shared.identity.value_objects import (  # noqa: F401
    AuthMethod,
    ClientId,
    ClientType,
    CodeChallenge,
    Email,
    GrantType,
    Password,
    RedirectUri,
    ResponseType,
    Scope,
    SubjectId,
    TokenType,
)

__all__ = [
    "AuthMethod",
    "ClientId",
    "ClientType",
    "CodeChallenge",
    "Email",
    "GrantType",
    "Password",
    "RedirectUri",
    "ResponseType",
    "Scope",
    "SubjectId",
    "TokenType",
]
