"""Seed script for registering default OAuth2 clients.

This script registers the webshell-frontend and other default clients
needed for the microservices platform to function.

Usage:
    python -m scripts.seed_clients

Or import and call programmatically:
    from scripts.seed_clients import seed_default_clients
    await seed_default_clients(client_repository)
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

import structlog

from identity_service.domain.entities.client import (
    Client,
    ClientRedirectUri,
    ClientScope,
)
from identity_service.domain.value_objects import (
    AuthMethod,
    ClientType,
    GrantType,
    ResponseType,
    Scope,
)

if TYPE_CHECKING:
    from identity_service.domain.repositories.client_repository import ClientRepository

logger = structlog.get_logger()


# Default clients for the platform
DEFAULT_CLIENTS: list[dict] = [
    {
        "client_id": "webshell-frontend",
        "client_name": "WebShell Frontend Application",
        "client_description": "Enterprise web dashboard for the microservices platform",
        "client_type": ClientType.PUBLIC,
        "token_endpoint_auth_method": AuthMethod.NONE,
        "grant_types": [GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN],
        "response_types": [ResponseType.CODE],
        "require_pkce": True,
        "allow_plain_pkce": False,  # Only S256 allowed
        "is_first_party": True,  # Skip consent for internal apps
        "require_consent": False,
        "allowed_cors_origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://app.local.ags.com",
        ],
        "redirect_uris": [
            {"uri": "http://localhost:3000/api/auth/callback/identity-service", "is_default": True},
            {"uri": "http://127.0.0.1:3000/api/auth/callback/identity-service"},
            {"uri": "https://app.local.ags.com/api/auth/callback/identity-service"},
        ],
        "post_logout_redirect_uris": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://app.local.ags.com",
        ],
        "scopes": [
            {"scope": Scope.OPENID, "is_default": True},
            {"scope": Scope.PROFILE, "is_default": True},
            {"scope": Scope.EMAIL, "is_default": True},
            {"scope": Scope.OFFLINE_ACCESS, "is_default": False},  # Requires explicit request
        ],
    },
    {
        "client_id": "audit-service",
        "client_name": "Audit Service",
        "client_description": "Internal audit logging service (machine-to-machine)",
        "client_type": ClientType.CONFIDENTIAL,
        "token_endpoint_auth_method": AuthMethod.CLIENT_SECRET_BASIC,
        "grant_types": [GrantType.CLIENT_CREDENTIALS],
        "response_types": [ResponseType.CODE],
        "require_pkce": False,
        "is_first_party": True,
        "require_consent": False,
        "allowed_cors_origins": [],
        "redirect_uris": [],
        "post_logout_redirect_uris": [],
        "scopes": [
            {"scope": Scope.OPENID, "is_default": True},
        ],
    },
    {
        "client_id": "federation-gateway",
        "client_name": "Federation Gateway",
        "client_description": "GraphQL federation gateway (machine-to-machine)",
        "client_type": ClientType.CONFIDENTIAL,
        "token_endpoint_auth_method": AuthMethod.CLIENT_SECRET_BASIC,
        "grant_types": [GrantType.CLIENT_CREDENTIALS],
        "response_types": [ResponseType.CODE],
        "require_pkce": False,
        "is_first_party": True,
        "require_consent": False,
        "allowed_cors_origins": [],
        "redirect_uris": [],
        "post_logout_redirect_uris": [],
        "scopes": [
            {"scope": Scope.OPENID, "is_default": True},
        ],
    },
]


def create_client_from_config(config: dict) -> Client:
    """Create a Client entity from configuration dictionary.

    Args:
        config: Client configuration dictionary

    Returns:
        Configured Client entity ready for persistence
    """
    client_uuid = uuid.uuid4()

    # Create redirect URIs
    redirect_uris = [
        ClientRedirectUri(
            client_id=client_uuid,
            uri=uri_config["uri"],
            is_default=uri_config.get("is_default", False),
        )
        for uri_config in config.get("redirect_uris", [])
    ]

    # Create scopes
    scopes = [
        ClientScope(
            client_id=client_uuid,
            scope=scope_config["scope"] if isinstance(scope_config["scope"], str) else scope_config["scope"].value,
            is_default=scope_config.get("is_default", False),
        )
        for scope_config in config.get("scopes", [])
    ]

    return Client(
        id=client_uuid,
        client_id=config["client_id"],
        client_name=config["client_name"],
        client_description=config.get("client_description"),
        client_type=config["client_type"],
        token_endpoint_auth_method=config["token_endpoint_auth_method"],
        grant_types=config["grant_types"],
        response_types=config["response_types"],
        require_pkce=config.get("require_pkce", True),
        allow_plain_pkce=config.get("allow_plain_pkce", False),
        is_first_party=config.get("is_first_party", False),
        require_consent=config.get("require_consent", True),
        allowed_cors_origins=config.get("allowed_cors_origins", []),
        post_logout_redirect_uris=config.get("post_logout_redirect_uris", []),
        redirect_uris=redirect_uris,
        scopes=scopes,
        is_active=True,
    )


async def seed_client(repository: ClientRepository, config: dict) -> Client | None:
    """Seed a single client if it doesn't exist.

    Args:
        repository: Client repository instance
        config: Client configuration dictionary

    Returns:
        Created client or None if already exists
    """
    client_id = config["client_id"]

    # Check if client already exists
    existing = await repository.get_by_client_id(client_id)
    if existing:
        logger.info("Client already exists, skipping", client_id=client_id)
        return None

    # Create and persist client
    client = create_client_from_config(config)
    created = await repository.create(client)

    # Generate secret for confidential clients
    if client.client_type == ClientType.CONFIDENTIAL:
        plain_secret, _secret_entity = client.add_secret(
            description="Initial secret generated during seeding"
        )
        await repository.update(client)
        logger.info(
            "Created confidential client with secret",
            client_id=client_id,
            client_secret=plain_secret,  # Only shown once during seeding!
        )
    else:
        logger.info("Created public client", client_id=client_id)

    return created


async def seed_default_clients(repository: ClientRepository) -> list[Client]:
    """Seed all default clients.

    Args:
        repository: Client repository instance

    Returns:
        List of created clients (excludes already existing)
    """
    logger.info("Starting default client seeding", count=len(DEFAULT_CLIENTS))

    created_clients = []
    for config in DEFAULT_CLIENTS:
        client = await seed_client(repository, config)
        if client:
            created_clients.append(client)

    logger.info(
        "Client seeding complete",
        created=len(created_clients),
        skipped=len(DEFAULT_CLIENTS) - len(created_clients),
    )

    return created_clients


async def main() -> None:
    """Main entry point for CLI usage."""
    # Import here to avoid circular imports
    from identity_service.api.dependencies import get_client_repository

    repository = get_client_repository()
    await seed_default_clients(repository)


if __name__ == "__main__":
    asyncio.run(main())
