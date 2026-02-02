"""Admin API routes for OAuth2 client management.

Provides CRUD operations for managing OAuth2 clients.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from identity_admin_service.api.dependencies import get_client_repository
from shared.utils import now_utc

router = APIRouter(prefix="/api/admin/clients", tags=["admin-clients"])


# ============================================================================
# Enums (mirroring identity-service value objects)
# ============================================================================


class ClientType(str, Enum):
    """OAuth2 client type."""

    PUBLIC = "public"
    CONFIDENTIAL = "confidential"


class AuthMethod(str, Enum):
    """Token endpoint authentication method."""

    CLIENT_SECRET_BASIC = "client_secret_basic"
    CLIENT_SECRET_POST = "client_secret_post"
    NONE = "none"
    PRIVATE_KEY_JWT = "private_key_jwt"


class GrantType(str, Enum):
    """OAuth2 grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"
    IMPLICIT = "implicit"
    DEVICE_CODE = "device_code"


class ResponseType(str, Enum):
    """OAuth2 response types."""

    CODE = "code"
    TOKEN = "token"
    ID_TOKEN = "id_token"
    CODE_TOKEN = "code token"
    CODE_ID_TOKEN = "code id_token"
    TOKEN_ID_TOKEN = "token id_token"
    CODE_TOKEN_ID_TOKEN = "code token id_token"


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ClientScopeSchema(BaseModel):
    """Schema for client scope."""

    scope: str = Field(..., description="Scope name (e.g., 'openid', 'profile')")
    is_default: bool = Field(False, description="Whether this scope is granted by default")


class ClientRedirectUriSchema(BaseModel):
    """Schema for client redirect URI."""

    uri: str = Field(..., description="Redirect URI")
    is_default: bool = Field(False, description="Whether this is the default redirect URI")


class CreateClientRequest(BaseModel):
    """Request schema for creating an OAuth2 client."""

    client_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    client_description: str | None = Field(None, max_length=1000, description="Description")
    client_uri: str | None = Field(None, description="Homepage URL")
    logo_uri: str | None = Field(None, description="Logo URL")
    client_type: str = Field("confidential", description="'public' or 'confidential'")
    token_endpoint_auth_method: str = Field(
        "client_secret_basic",
        description="Authentication method: client_secret_basic, client_secret_post, none",
    )
    grant_types: list[str] = Field(
        default=["authorization_code", "refresh_token"],
        description="Allowed grant types",
    )
    response_types: list[str] = Field(
        default=["code"],
        description="Allowed response types",
    )
    redirect_uris: list[str] = Field(
        default=[],
        description="Registered redirect URIs",
    )
    scopes: list[str] = Field(
        default=["openid", "profile", "email"],
        description="Allowed scopes",
    )
    require_pkce: bool = Field(True, description="Require PKCE for authorization code flow")
    require_consent: bool = Field(True, description="Require user consent")
    is_first_party: bool = Field(False, description="First-party app (may skip consent)")
    allowed_cors_origins: list[str] = Field(default=[], description="Allowed CORS origins")
    access_token_lifetime: int | None = Field(
        None, ge=60, description="Access token lifetime in seconds"
    )
    refresh_token_lifetime: int | None = Field(
        None, ge=60, description="Refresh token lifetime in seconds"
    )


class UpdateClientRequest(BaseModel):
    """Request schema for updating an OAuth2 client."""

    client_name: str | None = Field(None, min_length=1, max_length=255)
    client_description: str | None = Field(None, max_length=1000)
    client_uri: str | None = Field(None)
    logo_uri: str | None = Field(None)
    token_endpoint_auth_method: str | None = Field(None)
    grant_types: list[str] | None = Field(None)
    response_types: list[str] | None = Field(None)
    require_pkce: bool | None = Field(None)
    require_consent: bool | None = Field(None)
    is_first_party: bool | None = Field(None)
    is_active: bool | None = Field(None)
    allowed_cors_origins: list[str] | None = Field(None)
    access_token_lifetime: int | None = Field(None, ge=60)
    refresh_token_lifetime: int | None = Field(None, ge=60)


class ClientSecretResponse(BaseModel):
    """Response schema for client secret (only shown once on creation)."""

    id: str
    description: str | None
    secret: str | None = None  # Only populated on creation
    expires_at: str | None
    created_at: str


class ClientResponse(BaseModel):
    """Response schema for OAuth2 client."""

    id: str
    client_id: str
    client_name: str
    client_description: str | None
    client_uri: str | None
    logo_uri: str | None
    client_type: str
    token_endpoint_auth_method: str
    grant_types: list[str]
    response_types: list[str]
    redirect_uris: list[str]
    scopes: list[str]
    require_pkce: bool
    require_consent: bool
    is_first_party: bool
    is_active: bool
    allowed_cors_origins: list[str]
    access_token_lifetime: int | None
    refresh_token_lifetime: int | None
    secrets_count: int
    created_at: str
    updated_at: str


class ClientListResponse(BaseModel):
    """Response schema for paginated client list."""

    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GenerateSecretRequest(BaseModel):
    """Request to generate a new client secret."""

    description: str | None = Field(None, max_length=255)
    expires_in_days: int | None = Field(None, ge=1, le=365, description="Days until expiration")


class GenerateSecretResponse(BaseModel):
    """Response with the generated secret (shown only once)."""

    id: str
    secret: str
    description: str | None
    expires_at: str | None
    created_at: str


class AddRedirectUriRequest(BaseModel):
    """Request to add a redirect URI."""

    uri: str = Field(..., description="Redirect URI to add")
    is_default: bool = Field(False, description="Set as default redirect URI")


class AddScopeRequest(BaseModel):
    """Request to add a scope."""

    scope: str = Field(..., description="Scope name to add")
    is_default: bool = Field(False, description="Grant by default without explicit request")


# ============================================================================
# Lightweight Domain Entities for Admin Service
# ============================================================================
# These are simplified versions that mirror identity-service entities
# For production, these would share the same database models


class ClientSecret:
    """Client secret entity."""

    def __init__(self, client_id, secret_hash, description=None, expires_at=None):
        self.id = uuid.uuid4()
        self.client_id = client_id
        self.secret_hash = secret_hash
        self.description = description
        self.expires_at = expires_at
        self.created_at = now_utc()
        self.is_revoked = False


class ClientRedirectUri:
    """Client redirect URI entity."""

    def __init__(self, client_id, uri, is_default=False):
        self.id = uuid.uuid4()
        self.client_id = client_id
        self.uri = uri
        self.is_default = is_default


class ClientScope:
    """Client scope entity."""

    def __init__(self, client_id, scope, is_default=False):
        self.id = uuid.uuid4()
        self.client_id = client_id
        self.scope = scope
        self.is_default = is_default


class Client:
    """OAuth2 Client entity."""

    def __init__(
        self,
        client_name,
        client_description=None,
        client_uri=None,
        logo_uri=None,
        client_type=ClientType.CONFIDENTIAL,
        token_endpoint_auth_method=AuthMethod.CLIENT_SECRET_BASIC,
        grant_types=None,
        response_types=None,
        require_pkce=True,
        require_consent=True,
        is_first_party=False,
        allowed_cors_origins=None,
        access_token_lifetime=None,
        refresh_token_lifetime=None,
    ):
        self.id = uuid.uuid4()
        self.client_id = secrets.token_urlsafe(24)
        self.client_name = client_name
        self.client_description = client_description
        self.client_uri = client_uri
        self.logo_uri = logo_uri
        self.client_type = client_type
        self.token_endpoint_auth_method = token_endpoint_auth_method
        self.grant_types = grant_types or [GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN]
        self.response_types = response_types or [ResponseType.CODE]
        self.require_pkce = require_pkce
        self.require_consent = require_consent
        self.is_first_party = is_first_party
        self.is_active = True
        self.allowed_cors_origins = allowed_cors_origins or []
        self.access_token_lifetime = access_token_lifetime
        self.refresh_token_lifetime = refresh_token_lifetime
        self.redirect_uris: list[ClientRedirectUri] = []
        self.scopes: list[ClientScope] = []
        self.secrets: list[ClientSecret] = []
        self.created_at = now_utc()
        self.updated_at = now_utc()


def _client_to_response(client: Client) -> ClientResponse:
    """Convert client entity to response schema."""
    return ClientResponse(
        id=str(client.id),
        client_id=client.client_id,
        client_name=client.client_name,
        client_description=client.client_description,
        client_uri=client.client_uri,
        logo_uri=client.logo_uri,
        client_type=client.client_type.value
        if isinstance(client.client_type, Enum)
        else client.client_type,
        token_endpoint_auth_method=client.token_endpoint_auth_method.value
        if isinstance(client.token_endpoint_auth_method, Enum)
        else client.token_endpoint_auth_method,
        grant_types=[g.value if isinstance(g, Enum) else g for g in client.grant_types],
        response_types=[r.value if isinstance(r, Enum) else r for r in client.response_types],
        redirect_uris=[ru.uri for ru in client.redirect_uris],
        scopes=[s.scope for s in client.scopes],
        require_pkce=client.require_pkce,
        require_consent=client.require_consent,
        is_first_party=client.is_first_party,
        is_active=client.is_active,
        allowed_cors_origins=client.allowed_cors_origins,
        access_token_lifetime=client.access_token_lifetime,
        refresh_token_lifetime=client.refresh_token_lifetime,
        secrets_count=len([s for s in client.secrets if not s.is_revoked]),
        created_at=client.created_at.isoformat(),
        updated_at=client.updated_at.isoformat(),
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_client_type(value: str) -> ClientType:
    """Parse client type string to enum."""
    mapping = {
        "public": ClientType.PUBLIC,
        "confidential": ClientType.CONFIDENTIAL,
    }
    if value.lower() not in mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid client_type: {value}. Must be 'public' or 'confidential'.",
        )
    return mapping[value.lower()]


def _parse_auth_method(value: str) -> AuthMethod:
    """Parse auth method string to enum."""
    mapping = {
        "client_secret_basic": AuthMethod.CLIENT_SECRET_BASIC,
        "client_secret_post": AuthMethod.CLIENT_SECRET_POST,
        "none": AuthMethod.NONE,
        "private_key_jwt": AuthMethod.PRIVATE_KEY_JWT,
    }
    if value.lower() not in mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token_endpoint_auth_method: {value}.",
        )
    return mapping[value.lower()]


def _parse_grant_types(values: list[str]) -> list[GrantType]:
    """Parse grant type strings to enums."""
    mapping = {
        "authorization_code": GrantType.AUTHORIZATION_CODE,
        "refresh_token": GrantType.REFRESH_TOKEN,
        "client_credentials": GrantType.CLIENT_CREDENTIALS,
        "password": GrantType.PASSWORD,
        "implicit": GrantType.IMPLICIT,
        "device_code": GrantType.DEVICE_CODE,
    }
    result = []
    for v in values:
        if v.lower() not in mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grant_type: {v}.",
            )
        result.append(mapping[v.lower()])
    return result


def _parse_response_types(values: list[str]) -> list[ResponseType]:
    """Parse response type strings to enums."""
    mapping = {
        "code": ResponseType.CODE,
        "token": ResponseType.TOKEN,
        "id_token": ResponseType.ID_TOKEN,
        "code token": ResponseType.CODE_TOKEN,
        "code id_token": ResponseType.CODE_ID_TOKEN,
        "token id_token": ResponseType.TOKEN_ID_TOKEN,
        "code token id_token": ResponseType.CODE_TOKEN_ID_TOKEN,
    }
    result = []
    for v in values:
        if v.lower() not in mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid response_type: {v}.",
            )
        result.append(mapping[v.lower()])
    return result


def _hash_secret(plain_secret: str) -> str:
    """Hash a client secret using SHA-256 (simplified for admin service)."""
    import hashlib

    return hashlib.sha256(plain_secret.encode()).hexdigest()


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("", response_model=ClientListResponse)
async def list_clients(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    include_inactive: bool = False,
    search: str | None = Query(None, description="Search by name or client_id"),
    client_repo=Depends(get_client_repository),
) -> ClientListResponse:
    """List all OAuth2 clients with pagination."""
    skip = (page - 1) * page_size

    if search:
        clients = await client_repo.search(
            query=search,
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = len(clients) + skip
    elif include_inactive:
        clients = await client_repo.search(
            query="",
            skip=skip,
            limit=page_size,
            include_inactive=True,
        )
        total = await client_repo.count(include_inactive=True)
    else:
        clients = await client_repo.list_active(skip=skip, limit=page_size)
        total = await client_repo.count(include_inactive=False)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ClientListResponse(
        items=[_client_to_response(c) for c in clients],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{client_uuid}", response_model=ClientResponse)
async def get_client(
    client_uuid: uuid.UUID,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Get a specific OAuth2 client by UUID."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )
    return _client_to_response(client)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    request: CreateClientRequest,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Create a new OAuth2 client."""
    # Parse enums
    client_type = _parse_client_type(request.client_type)
    auth_method = _parse_auth_method(request.token_endpoint_auth_method)
    grant_types = _parse_grant_types(request.grant_types)
    response_types = _parse_response_types(request.response_types)

    # Create client entity
    client = Client(
        client_name=request.client_name,
        client_description=request.client_description,
        client_uri=request.client_uri,
        logo_uri=request.logo_uri,
        client_type=client_type,
        token_endpoint_auth_method=auth_method,
        grant_types=grant_types,
        response_types=response_types,
        require_pkce=request.require_pkce,
        require_consent=request.require_consent,
        is_first_party=request.is_first_party,
        allowed_cors_origins=request.allowed_cors_origins,
        access_token_lifetime=request.access_token_lifetime,
        refresh_token_lifetime=request.refresh_token_lifetime,
    )

    # Add redirect URIs
    for i, uri in enumerate(request.redirect_uris):
        client.redirect_uris.append(
            ClientRedirectUri(
                client_id=client.id,
                uri=uri,
                is_default=(i == 0),
            )
        )

    # Add scopes
    for scope in request.scopes:
        client.scopes.append(
            ClientScope(
                client_id=client.id,
                scope=scope,
                is_default=(scope in ["openid"]),
            )
        )

    # Persist
    created = await client_repo.create(client)
    return _client_to_response(created)


@router.patch("/{client_uuid}", response_model=ClientResponse)
async def update_client(
    client_uuid: uuid.UUID,
    request: UpdateClientRequest,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Update an existing OAuth2 client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    # Apply updates
    if request.client_name is not None:
        client.client_name = request.client_name
    if request.client_description is not None:
        client.client_description = request.client_description
    if request.client_uri is not None:
        client.client_uri = request.client_uri
    if request.logo_uri is not None:
        client.logo_uri = request.logo_uri
    if request.token_endpoint_auth_method is not None:
        client.token_endpoint_auth_method = _parse_auth_method(request.token_endpoint_auth_method)
    if request.grant_types is not None:
        client.grant_types = _parse_grant_types(request.grant_types)
    if request.response_types is not None:
        client.response_types = _parse_response_types(request.response_types)
    if request.require_pkce is not None:
        client.require_pkce = request.require_pkce
    if request.require_consent is not None:
        client.require_consent = request.require_consent
    if request.is_first_party is not None:
        client.is_first_party = request.is_first_party
    if request.is_active is not None:
        client.is_active = request.is_active
    if request.allowed_cors_origins is not None:
        client.allowed_cors_origins = request.allowed_cors_origins
    if request.access_token_lifetime is not None:
        client.access_token_lifetime = request.access_token_lifetime
    if request.refresh_token_lifetime is not None:
        client.refresh_token_lifetime = request.refresh_token_lifetime

    client.updated_at = now_utc()

    updated = await client_repo.update(client)
    return _client_to_response(updated)


@router.delete("/{client_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_uuid: uuid.UUID,
    client_repo=Depends(get_client_repository),
) -> None:
    """Delete (deactivate) an OAuth2 client."""
    deleted = await client_repo.delete(client_uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )


@router.post("/{client_uuid}/activate", response_model=ClientResponse)
async def activate_client(
    client_uuid: uuid.UUID,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Activate an OAuth2 client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    client.is_active = True
    client.updated_at = now_utc()
    updated = await client_repo.update(client)
    return _client_to_response(updated)


@router.post("/{client_uuid}/deactivate", response_model=ClientResponse)
async def deactivate_client(
    client_uuid: uuid.UUID,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Deactivate an OAuth2 client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    client.is_active = False
    client.updated_at = now_utc()
    updated = await client_repo.update(client)
    return _client_to_response(updated)


@router.post(
    "/{client_uuid}/secrets",
    response_model=GenerateSecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_client_secret(
    client_uuid: uuid.UUID,
    request: GenerateSecretRequest,
    client_repo=Depends(get_client_repository),
) -> GenerateSecretResponse:
    """Generate a new client secret.

    The secret is returned only once in this response.
    Store it securely as it cannot be retrieved again.
    """
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    # Generate secret and hash
    plain_secret = secrets.token_urlsafe(32)
    hashed = _hash_secret(plain_secret)

    expires_at = None
    if request.expires_in_days:
        expires_at = now_utc() + timedelta(days=request.expires_in_days)

    secret = ClientSecret(
        client_id=client.id,
        secret_hash=hashed,
        description=request.description,
        expires_at=expires_at,
    )
    client.secrets.append(secret)
    client.updated_at = now_utc()

    await client_repo.update(client)

    return GenerateSecretResponse(
        id=str(secret.id),
        secret=plain_secret,
        description=secret.description,
        expires_at=secret.expires_at.isoformat() if secret.expires_at else None,
        created_at=secret.created_at.isoformat(),
    )


@router.delete("/{client_uuid}/secrets/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_client_secret(
    client_uuid: uuid.UUID,
    secret_id: uuid.UUID,
    client_repo=Depends(get_client_repository),
) -> None:
    """Revoke a client secret."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    # Find and revoke secret
    for secret in client.secrets:
        if secret.id == secret_id:
            secret.is_revoked = True
            client.updated_at = now_utc()
            await client_repo.update(client)
            return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Secret {secret_id} not found",
    )


@router.post("/{client_uuid}/redirect-uris", response_model=ClientResponse)
async def add_redirect_uri(
    client_uuid: uuid.UUID,
    request: AddRedirectUriRequest,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Add a redirect URI to a client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    # Check for duplicates
    existing = [ru.uri for ru in client.redirect_uris]
    if request.uri in existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Redirect URI already exists: {request.uri}",
        )

    client.redirect_uris.append(
        ClientRedirectUri(
            client_id=client.id,
            uri=request.uri,
            is_default=request.is_default,
        )
    )
    client.updated_at = now_utc()

    updated = await client_repo.update(client)
    return _client_to_response(updated)


@router.delete("/{client_uuid}/redirect-uris", status_code=status.HTTP_204_NO_CONTENT)
async def remove_redirect_uri(
    client_uuid: uuid.UUID,
    uri: str = Query(..., description="Redirect URI to remove"),
    client_repo=Depends(get_client_repository),
) -> None:
    """Remove a redirect URI from a client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    original_count = len(client.redirect_uris)
    client.redirect_uris = [ru for ru in client.redirect_uris if ru.uri != uri]

    if len(client.redirect_uris) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Redirect URI not found: {uri}",
        )

    client.updated_at = now_utc()
    await client_repo.update(client)


@router.post("/{client_uuid}/scopes", response_model=ClientResponse)
async def add_scope(
    client_uuid: uuid.UUID,
    request: AddScopeRequest,
    client_repo=Depends(get_client_repository),
) -> ClientResponse:
    """Add a scope to a client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    # Check for duplicates
    existing = [s.scope for s in client.scopes]
    if request.scope in existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scope already exists: {request.scope}",
        )

    client.scopes.append(
        ClientScope(
            client_id=client.id,
            scope=request.scope,
            is_default=request.is_default,
        )
    )
    client.updated_at = now_utc()

    updated = await client_repo.update(client)
    return _client_to_response(updated)


@router.delete("/{client_uuid}/scopes", status_code=status.HTTP_204_NO_CONTENT)
async def remove_scope(
    client_uuid: uuid.UUID,
    scope: str = Query(..., description="Scope to remove"),
    client_repo=Depends(get_client_repository),
) -> None:
    """Remove a scope from a client."""
    client = await client_repo.get_by_id(client_uuid)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_uuid} not found",
        )

    original_count = len(client.scopes)
    client.scopes = [s for s in client.scopes if s.scope != scope]

    if len(client.scopes) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope not found: {scope}",
        )

    client.updated_at = now_utc()
    await client_repo.update(client)
