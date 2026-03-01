"""OAuth2 Client domain entity - re-exported from shared library.

Canonical definitions live in ``shared.identity.entities.client``.
"""

from shared.identity.entities.client import (  # noqa: F401
    Client,
    ClientRedirectUri,
    ClientScope,
    ClientSecret,
)

__all__ = [
    "Client",
    "ClientRedirectUri",
    "ClientScope",
    "ClientSecret",
]
