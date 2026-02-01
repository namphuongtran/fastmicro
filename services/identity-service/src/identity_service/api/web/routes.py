"""Web routes for login and consent pages.

Human-facing web endpoints for authentication flows.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from identity_service.api.dependencies import get_oauth2_service
from identity_service.application.services.oauth2_service import OAuth2Service

router = APIRouter(tags=["web"])

# Templates configuration - will be set up in main.py
templates: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    """Get templates instance."""
    if templates is None:
        raise RuntimeError("Templates not initialized")
    return templates


def _get_year() -> int:
    """Get current year for footer."""
    return datetime.now().year


# Session management (simplified - in production use Redis)
_sessions: dict[str, dict[str, Any]] = {}


def _get_session(request: Request) -> dict[str, Any]:
    """Get or create session from cookie."""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    return {}


def _set_session(response: Response, session_data: dict[str, Any]) -> str:
    """Create or update session."""
    session_id = str(uuid4())
    _sessions[session_id] = session_data
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,  # 1 hour
    )
    return session_id


def _clear_session(response: Response, session_id: str | None) -> None:
    """Clear session."""
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    response.delete_cookie("session_id")


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    response_type: str | None = None,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    scope: str | None = None,
    state: str | None = None,
    nonce: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    login_hint: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """Render login page."""
    tpl = get_templates()

    # Check if user is already logged in
    session = _get_session(request)
    if session.get("user_id"):
        # User is logged in, redirect to consent
        query_params = []
        if response_type:
            query_params.append(f"response_type={response_type}")
        if client_id:
            query_params.append(f"client_id={client_id}")
        if redirect_uri:
            query_params.append(f"redirect_uri={redirect_uri}")
        if scope:
            query_params.append(f"scope={scope}")
        if state:
            query_params.append(f"state={state}")
        if nonce:
            query_params.append(f"nonce={nonce}")
        if code_challenge:
            query_params.append(f"code_challenge={code_challenge}")
            query_params.append(f"code_challenge_method={code_challenge_method or 'plain'}")

        consent_url = "/consent?" + "&".join(query_params) if query_params else "/consent"
        return RedirectResponse(url=consent_url, status_code=status.HTTP_302_FOUND)

    # Get client name if client_id provided
    client_name = None
    if client_id:
        # In production, fetch from client repository
        client_name = client_id  # Simplified

    return tpl.TemplateResponse(
        "login.html",
        {
            "request": request,
            "year": _get_year(),
            "response_type": response_type or "",
            "client_id": client_id or "",
            "redirect_uri": redirect_uri or "",
            "scope": scope or "",
            "state": state or "",
            "nonce": nonce or "",
            "code_challenge": code_challenge or "",
            "code_challenge_method": code_challenge_method or "",
            "login_hint": login_hint or "",
            "client_name": client_name,
            "error": error,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    response_type: Annotated[str, Form()] = "",
    client_id: Annotated[str, Form()] = "",
    redirect_uri: Annotated[str, Form()] = "",
    scope: Annotated[str, Form()] = "",
    state: Annotated[str, Form()] = "",
    nonce: Annotated[str, Form()] = "",
    code_challenge: Annotated[str, Form()] = "",
    code_challenge_method: Annotated[str, Form()] = "",
    remember: Annotated[bool, Form()] = False,
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> Response:
    """Handle login form submission."""
    tpl = get_templates()

    # Authenticate user
    result = await oauth2_service.login(email, password)

    if not result.success:
        return tpl.TemplateResponse(
            "login.html",
            {
                "request": request,
                "year": _get_year(),
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "login_hint": email,
                "client_name": client_id,
                "error": result.error_description or "Invalid credentials",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Create session
    response = RedirectResponse(
        url="/consent?"
        + "&".join(
            [
                f"response_type={response_type}",
                f"client_id={client_id}",
                f"redirect_uri={redirect_uri}",
                f"scope={scope}",
                f"state={state}",
                f"nonce={nonce}",
                f"code_challenge={code_challenge}",
                f"code_challenge_method={code_challenge_method}",
            ]
        )
        if client_id
        else "/",
        status_code=status.HTTP_302_FOUND,
    )

    _set_session(
        response,
        {
            "user_id": result.user_id,
            "email": email,
            "remember": remember,
        },
    )

    return response


@router.get("/consent", response_class=HTMLResponse)
async def consent_page(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str | None = None,
    nonce: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> Response:
    """Render consent page."""
    tpl = get_templates()

    # Check if user is logged in
    session = _get_session(request)
    if not session.get("user_id"):
        # Redirect to login
        query_params = [
            f"response_type={response_type}",
            f"client_id={client_id}",
            f"redirect_uri={redirect_uri}",
            f"scope={scope}",
        ]
        if state:
            query_params.append(f"state={state}")
        if nonce:
            query_params.append(f"nonce={nonce}")
        if code_challenge:
            query_params.append(f"code_challenge={code_challenge}")
            query_params.append(f"code_challenge_method={code_challenge_method or 'plain'}")

        return RedirectResponse(
            url="/login?" + "&".join(query_params),
            status_code=status.HTTP_302_FOUND,
        )

    # Check for existing consent
    user_id = session["user_id"]
    has_consent = await oauth2_service.check_consent(user_id, client_id, scope.split())

    if has_consent:
        # Skip consent page, generate code directly
        return await _process_consent_allow(
            request=request,
            user_id=user_id,
            user_email=session["email"],
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            oauth2_service=oauth2_service,
        )

    # Parse scopes for display
    scope_descriptions = {
        "openid": ("OpenID", "Access your basic profile"),
        "profile": ("Profile", "View your name and profile information"),
        "email": ("Email", "View your email address"),
        "offline_access": ("Offline Access", "Access your data when you're not present"),
    }

    scopes = []
    for s in scope.split():
        name, description = scope_descriptions.get(s, (s, f"Access to {s}"))
        scopes.append({"name": name, "description": description})

    return tpl.TemplateResponse(
        "consent.html",
        {
            "request": request,
            "year": _get_year(),
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state or "",
            "nonce": nonce or "",
            "code_challenge": code_challenge or "",
            "code_challenge_method": code_challenge_method or "",
            "client_name": client_id,  # In production, fetch from client repository
            "client_logo": None,
            "scopes": scopes,
            "user_email": session["email"],
        },
    )


@router.post("/consent", response_class=HTMLResponse)
async def consent_submit(
    request: Request,
    action: Annotated[str, Form()],
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    scope: Annotated[str, Form()],
    state: Annotated[str, Form()] = "",
    nonce: Annotated[str, Form()] = "",
    code_challenge: Annotated[str, Form()] = "",
    code_challenge_method: Annotated[str, Form()] = "",
    remember_consent: Annotated[bool, Form()] = False,
    oauth2_service: OAuth2Service = Depends(get_oauth2_service),
) -> Response:
    """Handle consent form submission."""
    tpl = get_templates()

    # Check if user is logged in
    session = _get_session(request)
    if not session.get("user_id"):
        return tpl.TemplateResponse(
            "error.html",
            {
                "request": request,
                "year": _get_year(),
                "error_title": "Session Expired",
                "error_description": "Your session has expired. Please sign in again.",
                "error_code": "session_expired",
                "return_url": f"/login?client_id={client_id}&redirect_uri={redirect_uri}",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user_id = session["user_id"]
    user_email = session["email"]

    if action == "deny":
        # User denied consent
        error_url = f"{redirect_uri}?error=access_denied&error_description=User%20denied%20consent"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

    # Save consent if requested
    if remember_consent:
        await oauth2_service.save_consent(user_id, client_id, scope.split())

    return await _process_consent_allow(
        request=request,
        user_id=user_id,
        user_email=user_email,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        oauth2_service=oauth2_service,
    )


async def _process_consent_allow(
    request: Request,
    user_id: str,
    user_email: str,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str | None,
    nonce: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
    oauth2_service: OAuth2Service,
) -> Response:
    """Process consent allow action and generate authorization code."""
    tpl = get_templates()

    # Generate authorization code
    try:
        result = await oauth2_service.create_authorization_code(
            user_id=user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope.split(),
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Build redirect URL with code
        callback_url = f"{redirect_uri}?code={result.code}"
        if state:
            callback_url += f"&state={state}"

        return RedirectResponse(url=callback_url, status_code=status.HTTP_302_FOUND)

    except Exception as e:
        return tpl.TemplateResponse(
            "error.html",
            {
                "request": request,
                "year": _get_year(),
                "error_title": "Authorization Failed",
                "error_description": str(e),
                "error_code": "server_error",
                "return_url": redirect_uri,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/logout", response_class=HTMLResponse)
async def logout(
    request: Request,
    post_logout_redirect: str | None = None,
) -> Response:
    """Handle logout."""
    session_id = request.cookies.get("session_id")

    redirect_url = post_logout_redirect or "/"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    _clear_session(response, session_id)

    return response


@router.get("/error", response_class=HTMLResponse)
async def error_page(
    request: Request,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    """Render error page."""
    tpl = get_templates()

    return tpl.TemplateResponse(
        "error.html",
        {
            "request": request,
            "year": _get_year(),
            "error_title": "Error",
            "error_description": error_description or "An error occurred",
            "error_code": error,
            "return_url": None,
        },
    )
