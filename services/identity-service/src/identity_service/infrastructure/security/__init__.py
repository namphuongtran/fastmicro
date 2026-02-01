"""Security infrastructure package."""

from identity_service.infrastructure.security.brute_force import (
    AccountLockStatus,
    BruteForceProtectionService,
    IPStatus,
    LoginAttempt,
    LockoutReason,
    get_brute_force_protection_service,
)
from identity_service.infrastructure.security.jwt_service import (
    JWTService,
    KeyManager,
    get_jwt_service,
    get_key_manager,
)
from identity_service.infrastructure.security.password_policy import (
    PasswordPolicyService,
    PasswordStrength,
    PasswordValidationResult,
    add_to_password_history,
    get_password_policy_service,
    is_password_expired,
)
from identity_service.infrastructure.security.password_service import (
    PasswordService,
    get_password_service,
)
from identity_service.infrastructure.security.sessions import (
    SessionInfo,
    SessionManagementService,
    SessionStatus,
    get_session_management_service,
)

__all__ = [
    # JWT
    "JWTService",
    "KeyManager",
    "get_jwt_service",
    "get_key_manager",
    # Password
    "PasswordService",
    "get_password_service",
    # Password Policy
    "PasswordPolicyService",
    "PasswordStrength",
    "PasswordValidationResult",
    "add_to_password_history",
    "get_password_policy_service",
    "is_password_expired",
    # Brute Force
    "AccountLockStatus",
    "BruteForceProtectionService",
    "IPStatus",
    "LoginAttempt",
    "LockoutReason",
    "get_brute_force_protection_service",
    # Sessions
    "SessionInfo",
    "SessionManagementService",
    "SessionStatus",
    "get_session_management_service",
]
