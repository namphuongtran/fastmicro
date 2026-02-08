"""User Authentication Service — orchestrates registration, login, and password flows."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from identity_service.application.dtos import LoginResult, RegistrationResult
from identity_service.domain.entities.password_reset import PasswordResetToken
from identity_service.domain.entities.user import User, UserCredential, UserProfile
from shared.observability import get_structlog_logger
from shared.utils import now_utc

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings
    from identity_service.domain.repositories import PasswordResetRepository, UserRepository
    from identity_service.infrastructure.security import (
        BruteForceProtectionService,
        JWTService,
        PasswordPolicyService,
        PasswordService,
        SessionManagementService,
    )

logger = get_structlog_logger(__name__)


class UserAuthService:
    """Application service for user authentication operations.

    Orchestrates domain entities and infrastructure services for:
    - User registration with password policy validation
    - Login with brute force protection and account lockout
    - Password change with history tracking
    - Password reset token management
    """

    def __init__(
        self,
        settings: Settings,
        user_repository: UserRepository,
        password_reset_repository: PasswordResetRepository,
        password_service: PasswordService,
        password_policy_service: PasswordPolicyService,
        brute_force_service: BruteForceProtectionService,
        session_service: SessionManagementService,
        jwt_service: JWTService,
    ) -> None:
        """Initialize UserAuthService with all dependencies."""
        self._settings = settings
        self._user_repo = user_repository
        self._reset_repo = password_reset_repository
        self._password_service = password_service
        self._password_policy = password_policy_service
        self._brute_force = brute_force_service
        self._session_service = session_service
        self._jwt_service = jwt_service

    # =========================================================================
    # Registration
    # =========================================================================

    async def register(
        self,
        email: str,
        password: str,
        username: str | None = None,
        given_name: str | None = None,
        family_name: str | None = None,
    ) -> RegistrationResult:
        """Register a new user.

        Args:
            email: User email address.
            password: Plain text password.
            username: Optional username.
            given_name: Optional first name.
            family_name: Optional last name.

        Returns:
            RegistrationResult with success status.
        """
        # Check if email already exists
        if await self._user_repo.exists_by_email(email):
            logger.warning("Registration attempt with existing email", email=email)
            return RegistrationResult(
                success=False,
                error="email_exists",
                errors=["An account with this email already exists"],
            )

        # Check if username already exists
        if username and await self._user_repo.exists_by_username(username):
            logger.warning("Registration attempt with existing username", username=username)
            return RegistrationResult(
                success=False,
                error="username_exists",
                errors=["This username is already taken"],
            )

        # Validate password against policy
        policy_result = self._password_policy.validate_password(password, email=email)
        if not policy_result.is_valid:
            return RegistrationResult(
                success=False,
                error="weak_password",
                errors=policy_result.errors,
            )

        # Hash password
        password_hash = self._password_service.hash_password(password)

        # Create user entity
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=email,
            username=username,
            credential=UserCredential(
                user_id=user_id,
                password_hash=password_hash,
                last_password_change=now_utc(),
            ),
            profile=UserProfile(
                user_id=user_id,
                given_name=given_name,
                family_name=family_name,
                preferred_username=username,
            ),
        )

        # Persist user
        created_user = await self._user_repo.create(user)

        logger.info(
            "User registered successfully",
            user_id=str(created_user.id),
            email=email,
        )

        return RegistrationResult(
            success=True,
            user_id=created_user.id,
        )

    # =========================================================================
    # Login
    # =========================================================================

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        """Authenticate user with email and password.

        Includes brute force protection, account lockout, and MFA checks.

        Args:
            email: User email address.
            password: Plain text password.
            ip_address: Client IP for rate limiting.
            user_agent: Client user agent for session tracking.

        Returns:
            LoginResult with tokens or error/MFA prompt.
        """
        # Check brute force protection
        account_status = self._brute_force.check_account(email)
        if account_status.is_locked:
            logger.warning(
                "Login attempt on locked account",
                email=email,
                locked_until=str(account_status.unlock_at),
            )
            return LoginResult(
                success=False,
                error="account_locked",
            )

        # Check IP-based rate limiting
        if ip_address:
            ip_status = self._brute_force.check_ip(ip_address)
            if ip_status.is_blocked:
                logger.warning(
                    "Login attempt from blocked IP",
                    ip_address=ip_address,
                )
                return LoginResult(success=False, error="ip_blocked")

        # Progressive delay check
        if account_status.required_delay_seconds > 0:
            logger.info(
                "Progressive delay applied",
                email=email,
                delay=account_status.required_delay_seconds,
            )
            return LoginResult(
                success=False,
                error="too_many_attempts",
            )

        # Find user
        user = await self._user_repo.get_by_email(email)
        if not user:
            # Record failed attempt (prevents email enumeration timing attacks)
            self._brute_force.record_attempt(
                email,
                ip_address or "unknown",
                success=False,
                user_agent=user_agent,
                failure_reason="user_not_found",
            )
            return LoginResult(success=False, error="invalid_credentials")

        # Check if user can login
        can_login, reason = user.can_login()
        if not can_login:
            return LoginResult(success=False, error=reason or "login_disabled")

        # Verify password
        if not user.credential or not self._password_service.verify_password(
            password, user.credential.password_hash
        ):
            # Record failed attempt
            self._brute_force.record_attempt(
                email,
                ip_address or "unknown",
                success=False,
                user_agent=user_agent,
                failure_reason="invalid_password",
            )
            user.credential.increment_failed_attempts(
                max_attempts=self._settings.login_max_attempts,
                lockout_duration=self._settings.login_lockout_duration,
            )
            await self._user_repo.update(user)

            logger.warning(
                "Failed login attempt",
                email=email,
                failed_attempts=user.credential.failed_login_attempts,
            )
            return LoginResult(success=False, error="invalid_credentials")

        # Successful password verification — check MFA
        if user.credential.mfa_enabled:
            # Generate temporary MFA token
            mfa_token = self._jwt_service.create_mfa_token(
                subject=str(user.id),
                expires_in=300,  # 5 minutes to complete MFA
            )
            logger.info("MFA required", user_id=str(user.id))
            return LoginResult(
                success=False,
                requires_mfa=True,
                mfa_token=mfa_token,
                user_id=user.id,
            )

        # Complete login (no MFA)
        return await self._complete_login(user, ip_address, user_agent)

    async def _complete_login(
        self,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        """Complete login after successful authentication (and MFA if required).

        Args:
            user: Authenticated user entity.
            ip_address: Client IP address.
            user_agent: Client user agent.

        Returns:
            LoginResult with tokens and session.
        """
        # Reset failed attempts
        self._brute_force.record_attempt(
            user.email,
            ip_address or "unknown",
            success=True,
        )
        if user.credential:
            user.credential.reset_failed_attempts()
            # Check if password hash needs upgrade (bcrypt -> argon2)
            await self._user_repo.update(user)

        # Create session
        session_result = self._session_service.create_session(
            user_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Generate tokens
        access_token, _jti, expires_in = self._jwt_service.create_access_token(
            subject=str(user.id),
            client_id="identity-service",
            scope="openid profile email",
            claims={"roles": user.get_active_roles()} if user.roles else None,
        )

        _refresh_token_value: str | None = None
        # For direct login, always provide refresh token
        from identity_service.domain.entities import RefreshToken

        refresh_token = RefreshToken(
            client_id="identity-service",
            user_id=user.id,
            scope="openid profile email offline_access",
        )
        _refresh_token_value = refresh_token.token

        # Generate ID token (reserved for future OAuth2 flow)
        _id_token = self._jwt_service.create_id_token(
            subject=str(user.id),
            client_id="identity-service",
            claims={
                "email": user.email,
                "email_verified": user.email_verified,
                "name": user.get_display_name(),
            },
        )

        logger.info(
            "User logged in successfully",
            user_id=str(user.id),
            session_id=session_result.session_id,
        )

        return LoginResult(
            success=True,
            user_id=user.id,
            session_id=session_result.session_id,
        )

    # =========================================================================
    # Password Change
    # =========================================================================

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> tuple[bool, str | None]:
        """Change password for authenticated user.

        Args:
            user_id: Authenticated user's ID.
            current_password: Current password for verification.
            new_password: New password.

        Returns:
            Tuple of (success, error_message).
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return False, "User not found"

        # Verify current password
        if not self._password_service.verify_password(
            current_password, user.credential.password_hash
        ):
            return False, "Current password is incorrect"

        # Validate new password against policy
        policy_result = self._password_policy.validate_password(
            new_password,
            user_id=str(user_id),
            verify_func=self._password_service.verify_password,
        )
        if not policy_result.is_valid:
            return False, "; ".join(policy_result.errors)

        # Ensure new password is different
        if self._password_service.verify_password(new_password, user.credential.password_hash):
            return False, "New password must be different from current password"

        # Hash and update
        from identity_service.infrastructure.security import add_to_password_history

        add_to_password_history(str(user_id), user.credential.password_hash)
        user.credential.password_hash = self._password_service.hash_password(new_password)
        user.credential.last_password_change = now_utc()
        user.credential.updated_at = now_utc()

        await self._user_repo.update(user)

        logger.info("Password changed", user_id=str(user_id))
        return True, None

    # =========================================================================
    # Password Reset
    # =========================================================================

    async def request_password_reset(
        self,
        email: str,
        ip_address: str | None = None,
    ) -> str | None:
        """Create a password reset token.

        Always returns None to the caller (prevent email enumeration),
        but returns the token value for internal use (e.g., sending email).

        Args:
            email: User email address.
            ip_address: Client IP address.

        Returns:
            Reset token string if user exists, None otherwise.
        """
        user = await self._user_repo.get_by_email(email)
        if not user:
            logger.info("Password reset requested for unknown email", email=email)
            return None

        # Invalidate any existing reset tokens
        await self._reset_repo.delete_for_user(user.id)

        # Create new reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            email=email,
            ip_address=ip_address,
        )
        await self._reset_repo.save(reset_token)

        logger.info(
            "Password reset token created",
            user_id=str(user.id),
            email=email,
        )

        return reset_token.token

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> tuple[bool, str | None]:
        """Reset password using a reset token.

        Args:
            token: Password reset token.
            new_password: New password.

        Returns:
            Tuple of (success, error_message).
        """
        # Find and validate token
        reset_token = await self._reset_repo.get_by_token(token)
        if not reset_token or not reset_token.is_valid():
            return False, "Invalid or expired reset token"

        # Find user
        user = await self._user_repo.get_by_id(reset_token.user_id)
        if not user or not user.credential:
            return False, "User not found"

        # Validate new password
        policy_result = self._password_policy.validate_password(
            new_password,
            user_id=str(user.id),
            verify_func=self._password_service.verify_password,
        )
        if not policy_result.is_valid:
            return False, "; ".join(policy_result.errors)

        # Hash and update
        from identity_service.infrastructure.security import add_to_password_history

        add_to_password_history(str(user.id), user.credential.password_hash)
        user.credential.password_hash = self._password_service.hash_password(new_password)
        user.credential.last_password_change = now_utc()
        user.credential.reset_failed_attempts()

        await self._user_repo.update(user)

        # Consume token and clean up
        reset_token.consume()
        await self._reset_repo.mark_as_used(token)
        await self._reset_repo.delete_for_user(user.id)

        logger.info("Password reset completed", user_id=str(user.id))
        return True, None
