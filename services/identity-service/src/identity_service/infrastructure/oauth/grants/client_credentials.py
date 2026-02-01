"""Client Credentials Grant implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from authlib.oauth2.rfc6749 import grants

if TYPE_CHECKING:
    from identity_service.domain.entities import Client


class ClientCredentialsGrant(grants.ClientCredentialsGrant):
    """Client Credentials Grant for machine-to-machine authentication.

    Implements RFC 6749 Section 4.4.
    Used by confidential clients to obtain access tokens without user involvement.
    """

    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
    ]

    def authenticate_user(self, client: Client) -> None:
        """No user authentication in client credentials flow.

        Args:
            client: Authenticated OAuth2 client

        Returns:
            None - client credentials grant has no user context.
        """
        return None
