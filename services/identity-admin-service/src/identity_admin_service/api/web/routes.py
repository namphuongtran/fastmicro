"""Admin web routes for identity administration.

Serves HTML pages for managing OAuth2 clients, users, and settings.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from identity_admin_service.api.dependencies import get_client_repository, get_user_repository

router = APIRouter(prefix="/admin", tags=["admin-web"])

# Templates will be set from main.py
templates: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    """Get templates instance."""
    if templates is None:
        raise RuntimeError("Admin templates not initialized")
    return templates


def _get_year() -> int:
    """Get current year for footer."""
    return datetime.now().year


def _format_date_display(dt: datetime) -> str:
    """Format datetime for display."""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            return f"{minutes} min ago" if minutes > 0 else "Just now"
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")


# ============================================================================
# Dashboard
# ============================================================================


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    client_repo=Depends(get_client_repository),
    user_repo=Depends(get_user_repository),
) -> HTMLResponse:
    """Render admin dashboard page."""
    tmpl = get_templates()

    # Gather stats
    total_clients = await client_repo.count(include_inactive=True)
    active_clients = await client_repo.count(include_inactive=False)
    total_users = await user_repo.count(include_inactive=True)

    # Get recent clients
    recent_clients = await client_repo.list_active(skip=0, limit=5)
    recent_clients_data = [
        {
            "id": str(c.id),
            "client_name": c.client_name,
            "client_type": c.client_type.value
            if hasattr(c.client_type, "value")
            else c.client_type,
            "is_active": c.is_active,
        }
        for c in recent_clients
    ]

    # Stats for dashboard
    stats = {
        "total_users": total_users,
        "new_users_today": 0,
        "total_clients": total_clients,
        "active_clients": active_clients,
        "active_sessions": 0,
        "tokens_issued_today": 0,
    }

    # Recent activity (placeholder)
    recent_activity: list[dict[str, Any]] = []

    return tmpl.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "year": _get_year(),
            "active_page": "dashboard",
            "stats": stats,
            "recent_clients": recent_clients_data,
            "recent_activity": recent_activity,
        },
    )


# ============================================================================
# Clients Management
# ============================================================================


@router.get("/clients", response_class=HTMLResponse)
async def admin_clients_list(
    request: Request,
    page: int = 1,
    search: str | None = None,
    status: str | None = None,
    client_type: str | None = None,
    client_repo=Depends(get_client_repository),
) -> HTMLResponse:
    """Render clients list page."""
    tmpl = get_templates()
    page_size = 20
    skip = (page - 1) * page_size

    include_inactive = status is None or status == "inactive"

    if search:
        clients = await client_repo.search(
            query=search,
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = len(clients) + skip
    else:
        if include_inactive and status is None:
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

    # Filter by client type if specified
    if client_type:
        type_value = client_type.lower()
        clients = [
            c
            for c in clients
            if (c.client_type.value if hasattr(c.client_type, "value") else c.client_type)
            == type_value
        ]

    # Filter by status
    if status == "active":
        clients = [c for c in clients if c.is_active]
    elif status == "inactive":
        clients = [c for c in clients if not c.is_active]

    # Convert to template data
    clients_data = [
        {
            "id": str(c.id),
            "client_id": c.client_id,
            "client_name": c.client_name,
            "client_description": c.client_description,
            "logo_uri": c.logo_uri,
            "client_type": c.client_type.value
            if hasattr(c.client_type, "value")
            else c.client_type,
            "grant_types": [g.value if hasattr(g, "value") else g for g in c.grant_types],
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat(),
            "created_at_display": _format_date_display(c.created_at),
        }
        for c in clients
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return tmpl.TemplateResponse(
        request=request,
        name="admin/clients.html",
        context={
            "year": _get_year(),
            "active_page": "clients",
            "clients": clients_data,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "search": search,
            "status": status,
            "client_type": client_type,
        },
    )


# ============================================================================
# Users Management
# ============================================================================


@router.get("/users", response_class=HTMLResponse)
async def admin_users_list(
    request: Request,
    page: int = 1,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    user_repo=Depends(get_user_repository),
) -> HTMLResponse:
    """Render users list page."""
    tmpl = get_templates()
    page_size = 20
    skip = (page - 1) * page_size

    include_inactive = status is None or status == "inactive"

    if role:
        users = await user_repo.find_by_role(role)
        if search:
            search_lower = search.lower()
            users = [
                u
                for u in users
                if search_lower in u.email.lower()
                or (u.username and search_lower in u.username.lower())
            ]
        if not include_inactive:
            users = [u for u in users if u.is_active]
        total = len(users)
        users = users[skip : skip + page_size]
    elif search:
        users = await user_repo.search(
            query=search,
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = len(users) + skip
    else:
        users = await user_repo.search(
            query="",
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive,
        )
        total = await user_repo.count(include_inactive=include_inactive)

    # Filter by status
    if status == "active":
        users = [u for u in users if u.is_active]
    elif status == "inactive":
        users = [u for u in users if not u.is_active]
    elif status == "locked":
        users = [u for u in users if u.credential and u.credential.is_locked()]

    # Convert to template data
    users_data = []
    for u in users:
        profile = u.profile
        credential = u.credential

        users_data.append(
            {
                "id": str(u.id),
                "email": u.email,
                "username": u.username,
                "full_name": profile.full_name if profile else None,
                "picture": profile.picture if profile else None,
                "email_verified": u.email_verified,
                "is_active": u.is_active,
                "is_locked": credential.is_locked() if credential else False,
                "mfa_enabled": credential.mfa_enabled if credential else False,
                "external_provider": u.external_provider,
                "roles": [r.role_name for r in u.roles if r.is_active()],
                "created_at": u.created_at.isoformat(),
                "created_at_display": _format_date_display(u.created_at),
            }
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # Get available roles for filter dropdown
    available_roles = ["admin", "user", "moderator"]

    return tmpl.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "year": _get_year(),
            "active_page": "users",
            "users": users_data,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "search": search,
            "status": status,
            "selected_role": role,
            "available_roles": available_roles,
        },
    )
