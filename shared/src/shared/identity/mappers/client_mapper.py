"""Client aggregate mappers: domain entity <-> ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from shared.identity.models.client import (
    ClientModel,
    ClientRedirectUriModel,
    ClientScopeModel,
    ClientSecretModel,
)

if TYPE_CHECKING:
    from shared.identity.entities import (
        Client,
        ClientRedirectUri,
        ClientScope,
        ClientSecret,
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def client_entity_to_model(entity: Client) -> ClientModel:
    """Convert Client domain entity to ORM model."""
    model = ClientModel(
        id=str(entity.id),
        client_id=entity.client_id,
        client_name=entity.client_name,
        client_description=entity.client_description,
        client_uri=entity.client_uri,
        logo_uri=entity.logo_uri,
        client_type=entity.client_type.value,
        token_endpoint_auth_method=entity.token_endpoint_auth_method.value,
        grant_types=",".join(g.value for g in entity.grant_types),
        response_types=",".join(r.value for r in entity.response_types),
        require_pkce=entity.require_pkce,
        allow_plain_pkce=entity.allow_plain_pkce,
        access_token_lifetime=entity.access_token_lifetime,
        refresh_token_lifetime=entity.refresh_token_lifetime,
        id_token_lifetime=entity.id_token_lifetime,
        require_consent=entity.require_consent,
        allow_remember_consent=entity.allow_remember_consent,
        allowed_cors_origins=",".join(entity.allowed_cors_origins)
        if entity.allowed_cors_origins
        else None,
        front_channel_logout_uri=entity.front_channel_logout_uri,
        back_channel_logout_uri=entity.back_channel_logout_uri,
        post_logout_redirect_uris=",".join(entity.post_logout_redirect_uris)
        if entity.post_logout_redirect_uris
        else None,
        is_active=entity.is_active,
        is_first_party=entity.is_first_party,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=str(entity.created_by) if entity.created_by else None,
    )

    model.secrets = [secret_entity_to_model(s) for s in entity.secrets]
    model.scopes = [scope_entity_to_model(s) for s in entity.scopes]
    model.redirect_uris = [redirect_uri_entity_to_model(r) for r in entity.redirect_uris]

    return model


def client_model_to_entity(model: ClientModel) -> Client:
    """Convert ORM model to Client domain entity."""
    from shared.identity.entities import (
        Client,
    )
    from shared.identity.value_objects import (
        AuthMethod,
        ClientType,
        GrantType,
        ResponseType,
    )

    grant_types = (
        [GrantType(g) for g in model.grant_types.split(",") if g] if model.grant_types else []
    )
    response_types = (
        [ResponseType(r) for r in model.response_types.split(",") if r]
        if model.response_types
        else []
    )
    cors_origins = (
        [o for o in model.allowed_cors_origins.split(",") if o]
        if model.allowed_cors_origins
        else []
    )
    post_logout = (
        [u for u in model.post_logout_redirect_uris.split(",") if u]
        if model.post_logout_redirect_uris
        else []
    )

    entity = Client(
        id=uuid.UUID(model.id),
        client_id=model.client_id,
        client_name=model.client_name,
        client_description=model.client_description,
        client_uri=model.client_uri,
        logo_uri=model.logo_uri,
        client_type=ClientType(model.client_type),
        token_endpoint_auth_method=AuthMethod(model.token_endpoint_auth_method),
        grant_types=grant_types,
        response_types=response_types,
        require_pkce=model.require_pkce,
        allow_plain_pkce=model.allow_plain_pkce,
        access_token_lifetime=model.access_token_lifetime,
        refresh_token_lifetime=model.refresh_token_lifetime,
        id_token_lifetime=model.id_token_lifetime,
        require_consent=model.require_consent,
        allow_remember_consent=model.allow_remember_consent,
        allowed_cors_origins=cors_origins,
        front_channel_logout_uri=model.front_channel_logout_uri,
        back_channel_logout_uri=model.back_channel_logout_uri,
        post_logout_redirect_uris=post_logout,
        is_active=model.is_active,
        is_first_party=model.is_first_party,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=uuid.UUID(model.created_by) if model.created_by else None,
    )

    entity.secrets = [secret_model_to_entity(s) for s in model.secrets]
    entity.scopes = [scope_model_to_entity(s) for s in model.scopes]
    entity.redirect_uris = [redirect_uri_model_to_entity(r) for r in model.redirect_uris]

    return entity


# ---------------------------------------------------------------------------
# ClientSecret
# ---------------------------------------------------------------------------


def secret_entity_to_model(entity: ClientSecret) -> ClientSecretModel:
    """Convert ClientSecret domain entity to ORM model."""
    return ClientSecretModel(
        id=str(entity.id),
        client_id=str(entity.client_id) if entity.client_id else None,
        secret_hash=entity.secret_hash,
        description=entity.description,
        expires_at=entity.expires_at,
        created_at=entity.created_at,
        last_used_at=entity.last_used_at,
        is_revoked=entity.is_revoked,
    )


def secret_model_to_entity(model: ClientSecretModel) -> ClientSecret:
    """Convert ORM model to ClientSecret domain entity."""
    from shared.identity.entities import ClientSecret

    return ClientSecret(
        id=uuid.UUID(model.id),
        client_id=uuid.UUID(model.client_id) if model.client_id else None,
        secret_hash=model.secret_hash,
        description=model.description,
        expires_at=model.expires_at,
        created_at=model.created_at,
        last_used_at=model.last_used_at,
        is_revoked=model.is_revoked,
    )


# ---------------------------------------------------------------------------
# ClientScope
# ---------------------------------------------------------------------------


def scope_entity_to_model(entity: ClientScope) -> ClientScopeModel:
    """Convert ClientScope domain entity to ORM model."""
    return ClientScopeModel(
        id=str(entity.id),
        client_id=str(entity.client_id) if entity.client_id else None,
        scope=entity.scope,
        is_default=entity.is_default,
    )


def scope_model_to_entity(model: ClientScopeModel) -> ClientScope:
    """Convert ORM model to ClientScope domain entity."""
    from shared.identity.entities import ClientScope

    return ClientScope(
        id=uuid.UUID(model.id),
        client_id=uuid.UUID(model.client_id) if model.client_id else None,
        scope=model.scope,
        is_default=model.is_default,
    )


# ---------------------------------------------------------------------------
# ClientRedirectUri
# ---------------------------------------------------------------------------


def redirect_uri_entity_to_model(entity: ClientRedirectUri) -> ClientRedirectUriModel:
    """Convert ClientRedirectUri domain entity to ORM model."""
    return ClientRedirectUriModel(
        id=str(entity.id),
        client_id=str(entity.client_id) if entity.client_id else None,
        uri=entity.uri,
        is_default=entity.is_default,
        created_at=entity.created_at,
    )


def redirect_uri_model_to_entity(model: ClientRedirectUriModel) -> ClientRedirectUri:
    """Convert ORM model to ClientRedirectUri domain entity."""
    from shared.identity.entities import ClientRedirectUri

    return ClientRedirectUri(
        id=uuid.UUID(model.id),
        client_id=uuid.UUID(model.client_id) if model.client_id else None,
        uri=model.uri,
        is_default=model.is_default,
        created_at=model.created_at,
    )
