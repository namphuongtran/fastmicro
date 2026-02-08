"""MFA (Multi-Factor Authentication) Service — TOTP setup, verification, recovery codes."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import pyotp

from shared.observability import get_structlog_logger
from shared.utils import now_utc

if TYPE_CHECKING:
    import uuid

    from identity_service.configs.settings import Settings
    from identity_service.domain.repositories import UserRepository
    from identity_service.infrastructure.security import JWTService, PasswordService

logger = get_structlog_logger(__name__)

# Number of recovery codes to generate
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 8


def _generate_recovery_codes(
    count: int = RECOVERY_CODE_COUNT,
    length: int = RECOVERY_CODE_LENGTH,
) -> list[str]:
    """Generate one-time recovery codes.

    Args:
        count: Number of codes to generate.
        length: Length of each code (characters).

    Returns:
        List of recovery code strings.
    """
    return [secrets.token_hex(length // 2).upper() for _ in range(count)]


class MFAService:
    """Application service for MFA/TOTP operations.

    Handles:
    - TOTP secret generation and provisioning URI
    - TOTP code verification
    - MFA enable/disable
    - Recovery code management
    """

    def __init__(
        self,
        settings: Settings,
        user_repository: UserRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
    ) -> None:
        """Initialize MFA service."""
        self._settings = settings
        self._user_repo = user_repository
        self._password_service = password_service
        self._jwt_service = jwt_service
        self._issuer_name = settings.app_name or "FastMicro Identity"

    # =========================================================================
    # Setup
    # =========================================================================

    async def setup_mfa(
        self, user_id: uuid.UUID
    ) -> tuple[str, str, list[str]] | tuple[None, None, None]:
        """Initiate MFA setup for a user.

        Generates a TOTP secret and recovery codes. MFA is not considered
        enabled until the user verifies a code from their authenticator.

        Args:
            user_id: User's UUID.

        Returns:
            Tuple of (secret, provisioning_uri, recovery_codes) or (None, None, None).
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return None, None, None

        if user.credential.mfa_enabled:
            logger.warning("MFA setup attempted on already-enabled account", user_id=str(user_id))
            return None, None, None

        # Generate TOTP secret
        secret = pyotp.random_base32()

        # Store secret (not yet enabled — requires verification)
        user.credential.mfa_secret = secret
        user.credential.updated_at = now_utc()

        # Generate recovery codes
        recovery_codes = _generate_recovery_codes()
        user.credential.recovery_codes = recovery_codes

        await self._user_repo.update(user)

        # Build provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self._issuer_name,
        )

        logger.info("MFA setup initiated", user_id=str(user_id))
        return secret, provisioning_uri, recovery_codes

    # =========================================================================
    # Verify and Enable
    # =========================================================================

    async def verify_and_enable(self, user_id: uuid.UUID, code: str) -> tuple[bool, str | None]:
        """Verify a TOTP code and enable MFA if valid.

        Called after setup to confirm the user has configured their
        authenticator app correctly.

        Args:
            user_id: User's UUID.
            code: 6-digit TOTP code from authenticator.

        Returns:
            Tuple of (success, error_message).
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return False, "User not found"

        if user.credential.mfa_enabled:
            return False, "MFA is already enabled"

        if not user.credential.mfa_secret:
            return False, "MFA setup not initiated. Call setup first."

        # Verify code
        totp = pyotp.TOTP(user.credential.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return False, "Invalid verification code"

        # Enable MFA
        user.credential.mfa_enabled = True
        user.credential.updated_at = now_utc()
        await self._user_repo.update(user)

        logger.info("MFA enabled", user_id=str(user_id))
        return True, None

    # =========================================================================
    # Login Verification
    # =========================================================================

    async def verify_login_code(
        self, mfa_token: str, code: str
    ) -> tuple[uuid.UUID | None, str | None]:
        """Verify TOTP code during login flow.

        Args:
            mfa_token: Temporary JWT from login step.
            code: 6-digit TOTP code.

        Returns:
            Tuple of (user_id, error_message). user_id is set on success.
        """
        # Decode MFA token
        claims = self._jwt_service.decode_token(mfa_token)
        if not claims or claims.get("type") != "mfa":
            return None, "Invalid or expired MFA token"

        user_id_str = claims.get("sub")
        if not user_id_str:
            return None, "Invalid MFA token"

        import uuid as uuid_mod

        try:
            user_id = uuid_mod.UUID(user_id_str)
        except ValueError:
            return None, "Invalid MFA token"

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential or not user.credential.mfa_secret:
            return None, "User not found or MFA not configured"

        # Verify TOTP
        totp = pyotp.TOTP(user.credential.mfa_secret)
        if not totp.verify(code, valid_window=1):
            logger.warning("Failed MFA verification", user_id=str(user_id))
            return None, "Invalid verification code"

        logger.info("MFA verification successful", user_id=str(user_id))
        return user_id, None

    # =========================================================================
    # Recovery Code
    # =========================================================================

    async def verify_recovery_code(
        self, mfa_token: str, recovery_code: str
    ) -> tuple[uuid.UUID | None, int, str | None]:
        """Verify a recovery code during login flow.

        Consumes the recovery code (one-time use).

        Args:
            mfa_token: Temporary JWT from login step.
            recovery_code: One-time recovery code.

        Returns:
            Tuple of (user_id, remaining_codes, error_message).
        """
        # Decode MFA token
        claims = self._jwt_service.decode_token(mfa_token)
        if not claims or claims.get("type") != "mfa":
            return None, 0, "Invalid or expired MFA token"

        user_id_str = claims.get("sub")
        if not user_id_str:
            return None, 0, "Invalid MFA token"

        import uuid as uuid_mod

        try:
            user_id = uuid_mod.UUID(user_id_str)
        except ValueError:
            return None, 0, "Invalid MFA token"

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return None, 0, "User not found"

        # Check recovery code
        normalized_code = recovery_code.strip().upper()
        if normalized_code not in user.credential.recovery_codes:
            logger.warning(
                "Invalid recovery code attempt",
                user_id=str(user_id),
            )
            return None, 0, "Invalid recovery code"

        # Consume recovery code
        user.credential.recovery_codes.remove(normalized_code)
        user.credential.updated_at = now_utc()
        await self._user_repo.update(user)

        remaining = len(user.credential.recovery_codes)
        logger.info(
            "Recovery code used",
            user_id=str(user_id),
            remaining_codes=remaining,
        )

        return user_id, remaining, None

    # =========================================================================
    # Disable
    # =========================================================================

    async def disable_mfa(
        self, user_id: uuid.UUID, password: str, code: str
    ) -> tuple[bool, str | None]:
        """Disable MFA for a user.

        Requires password and current TOTP code for security.

        Args:
            user_id: User's UUID.
            password: Current password for confirmation.
            code: Current TOTP code.

        Returns:
            Tuple of (success, error_message).
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return False, "User not found"

        if not user.credential.mfa_enabled:
            return False, "MFA is not enabled"

        # Verify password
        if not self._password_service.verify_password(password, user.credential.password_hash):
            return False, "Invalid password"

        # Verify TOTP
        if user.credential.mfa_secret:
            totp = pyotp.TOTP(user.credential.mfa_secret)
            if not totp.verify(code, valid_window=1):
                return False, "Invalid verification code"

        # Disable MFA
        user.credential.mfa_enabled = False
        user.credential.mfa_secret = None
        user.credential.recovery_codes = []
        user.credential.updated_at = now_utc()
        await self._user_repo.update(user)

        logger.info("MFA disabled", user_id=str(user_id))
        return True, None

    # =========================================================================
    # Status
    # =========================================================================

    async def get_mfa_status(self, user_id: uuid.UUID) -> tuple[bool, int]:
        """Get MFA status for a user.

        Args:
            user_id: User's UUID.

        Returns:
            Tuple of (mfa_enabled, recovery_codes_remaining).
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.credential:
            return False, 0

        return (
            user.credential.mfa_enabled,
            len(user.credential.recovery_codes),
        )
