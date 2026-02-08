"""Auth API router package.

Provides user-facing authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/password/change
- POST /api/v1/auth/password/forgot
- POST /api/v1/auth/password/reset
- POST /api/v1/auth/mfa/setup
- POST /api/v1/auth/mfa/verify
- POST /api/v1/auth/mfa/verify-login
- POST /api/v1/auth/mfa/recovery
- POST /api/v1/auth/mfa/disable
- GET  /api/v1/auth/mfa/status
"""

from fastapi import APIRouter

from identity_service.api.auth.login import router as login_router
from identity_service.api.auth.mfa import router as mfa_router
from identity_service.api.auth.password import router as password_router
from identity_service.api.auth.register import router as register_router

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

auth_router.include_router(register_router)
auth_router.include_router(login_router)
auth_router.include_router(password_router)
auth_router.include_router(mfa_router)

__all__ = ["auth_router"]
