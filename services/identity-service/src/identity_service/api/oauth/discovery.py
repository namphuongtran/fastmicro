"""OpenID Connect Discovery endpoint - .well-known/openid-configuration."""

from fastapi import APIRouter, Request

from identity_service.configs import get_settings

router = APIRouter(tags=["discovery"])


@router.get("/.well-known/openid-configuration")
async def get_openid_configuration(request: Request) -> dict:
    """Return OpenID Connect Discovery document.

    This endpoint provides clients with information about the IdP's
    capabilities and endpoints (RFC 8414).

    Returns:
        OpenID Provider Metadata dictionary.
    """
    settings = get_settings()
    issuer = settings.jwt_issuer

    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth2/authorize",
        "token_endpoint": f"{issuer}/oauth2/token",
        "userinfo_endpoint": f"{issuer}/oauth2/userinfo",
        "jwks_uri": f"{issuer}/.well-known/jwks.json",
        "revocation_endpoint": f"{issuer}/oauth2/revoke",
        "introspection_endpoint": f"{issuer}/oauth2/introspect",
        "end_session_endpoint": f"{issuer}/oauth2/logout",
        # Supported features
        "response_types_supported": [
            "code",
            "code id_token",
        ],
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "refresh_token",
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "offline_access",
        ],
        "claims_supported": [
            "sub",
            "name",
            "given_name",
            "family_name",
            "middle_name",
            "nickname",
            "preferred_username",
            "picture",
            "website",
            "gender",
            "birthdate",
            "zoneinfo",
            "locale",
            "email",
            "email_verified",
            "phone_number",
            "phone_number_verified",
            "address",
            "updated_at",
        ],
        "code_challenge_methods_supported": ["S256"],
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "response_modes_supported": ["query", "fragment"],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256"],
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "introspection_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "claims_parameter_supported": False,
        "service_documentation": f"{issuer}/docs",
    }


@router.get("/.well-known/jwks.json")
async def get_jwks(request: Request) -> dict:
    """Return JSON Web Key Set (JWKS).

    This endpoint provides the public keys used to verify
    JWT signatures (RFC 7517).

    Returns:
        JWKS containing public keys.
    """
    from identity_service.infrastructure.security import get_key_manager

    settings = get_settings()
    key_manager = get_key_manager(
        settings.jwt_private_key_path,
        settings.jwt_public_key_path,
    )
    return key_manager.get_jwks()
