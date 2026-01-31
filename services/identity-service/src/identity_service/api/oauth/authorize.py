"""OAuth2 Authorization endpoint - /oauth2/authorize."""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from identity_service.api.dependencies import get_oauth2_service
from identity_service.application.services import OAuth2Service

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


class AuthorizationRequest(BaseModel):
    """Authorization request parameters."""

    response_type: str
    client_id: str
    redirect_uri: str | None = None
    scope: str | None = None
    state: str | None = None
    nonce: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    prompt: str | None = None  # none, login, consent
    login_hint: str | None = None
    max_age: int | None = None


@router.get("/authorize")
async def authorization_endpoint(
    request: Request,
    response_type: Annotated[str, Query()],
    client_id: Annotated[str, Query()],
    oauth2_service: Annotated[OAuth2Service, Depends(get_oauth2_service)],
    redirect_uri: Annotated[str | None, Query()] = None,
    scope: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    nonce: Annotated[str | None, Query()] = None,
    code_challenge: Annotated[str | None, Query()] = None,
    code_challenge_method: Annotated[str | None, Query()] = None,
    prompt: Annotated[str | None, Query()] = None,
    login_hint: Annotated[str | None, Query()] = None,
    max_age: Annotated[int | None, Query()] = None,
) -> Response:
    """OAuth2 Authorization endpoint.

    Initiates the authorization flow by:
    1. Validating the client and request parameters
    2. Checking if user is authenticated
    3. Showing login page if needed
    4. Showing consent page if needed
    5. Redirecting back with authorization code

    Args:
        request: HTTP request
        response_type: Must be "code" or "code id_token"
        client_id: Client identifier
        redirect_uri: Where to redirect after authorization
        scope: Requested scope (space-separated)
        state: CSRF state parameter
        nonce: OpenID Connect nonce
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE method (must be S256)
        prompt: Login/consent behavior
        login_hint: Hint for username
        max_age: Max authentication age

    Returns:
        Redirect to login, consent, or callback URL.
    """
    # Validate client and redirect URI
    validation = await oauth2_service.validate_authorization_request(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        scope=scope,
    )

    if validation.is_error:
        # Redirect with error if we have a valid redirect_uri
        if validation.redirect_uri:
            error_params = {
                "error": validation.error,
                "error_description": validation.error_description,
            }
            if state:
                error_params["state"] = state
            return RedirectResponse(
                url=f"{validation.redirect_uri}?{urlencode(error_params)}",
                status_code=status.HTTP_302_FOUND,
            )

        # Otherwise show error page
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Error</title></head>
            <body>
                <h1>Authorization Error</h1>
                <p>Error: {validation.error}</p>
                <p>{validation.error_description}</p>
            </body>
            </html>
            """,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Check for existing session
    session_id = request.cookies.get("identity_session")
    user = None

    if session_id and prompt != "login":
        user = await oauth2_service.get_user_from_session(session_id)

    # If not authenticated, redirect to login
    if not user:
        login_params = {
            "response_type": response_type,
            "client_id": client_id,
            "scope": scope or "",
            "state": state or "",
        }
        if redirect_uri:
            login_params["redirect_uri"] = redirect_uri
        if nonce:
            login_params["nonce"] = nonce
        if code_challenge:
            login_params["code_challenge"] = code_challenge
        if code_challenge_method:
            login_params["code_challenge_method"] = code_challenge_method
        if login_hint:
            login_params["login_hint"] = login_hint

        return RedirectResponse(
            url=f"/login?{urlencode(login_params)}",
            status_code=status.HTTP_302_FOUND,
        )

    # Check if consent is needed
    needs_consent = await oauth2_service.needs_consent(
        user_id=user.id,
        client_id=client_id,
        scope=scope,
    )

    if needs_consent and prompt != "none":
        consent_params = {
            "response_type": response_type,
            "client_id": client_id,
            "scope": scope or "",
            "state": state or "",
        }
        if redirect_uri:
            consent_params["redirect_uri"] = redirect_uri
        if nonce:
            consent_params["nonce"] = nonce
        if code_challenge:
            consent_params["code_challenge"] = code_challenge
        if code_challenge_method:
            consent_params["code_challenge_method"] = code_challenge_method

        return RedirectResponse(
            url=f"/consent?{urlencode(consent_params)}",
            status_code=status.HTTP_302_FOUND,
        )

    # If prompt=none and needs consent/login, return error
    if prompt == "none" and (not user or needs_consent):
        error_params = {
            "error": "login_required" if not user else "consent_required",
        }
        if state:
            error_params["state"] = state
        return RedirectResponse(
            url=f"{validation.redirect_uri}?{urlencode(error_params)}",
            status_code=status.HTTP_302_FOUND,
        )

    # Generate authorization code
    code_result = await oauth2_service.create_authorization_code(
        user_id=user.id,
        client_id=client_id,
        redirect_uri=redirect_uri or validation.redirect_uri,
        scope=scope,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    # Redirect with code
    callback_params = {"code": code_result.code}
    if state:
        callback_params["state"] = state

    return RedirectResponse(
        url=f"{redirect_uri or validation.redirect_uri}?{urlencode(callback_params)}",
        status_code=status.HTTP_302_FOUND,
    )
