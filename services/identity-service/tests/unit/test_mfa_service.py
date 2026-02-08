"""Unit tests for MFAService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pyotp
import pytest

from identity_service.application.services.mfa_service import MFAService
from identity_service.domain.entities.user import User, UserCredential, UserProfile


# =============================================================================
# Helpers
# =============================================================================


def _make_user(
    mfa_enabled: bool = False,
    mfa_secret: str | None = None,
    recovery_codes: list[str] | None = None,
    password_hash: str = "hashed_pw",
) -> User:
    """Create a test user for MFA tests."""
    uid = uuid4()
    now = datetime.now(UTC)
    return User(
        id=uid,
        email="mfa@example.com",
        username="mfauser",
        is_active=True,
        created_at=now,
        updated_at=now,
        credential=UserCredential(
            user_id=uid,
            password_hash=password_hash,
            mfa_enabled=mfa_enabled,
            mfa_secret=mfa_secret,
            recovery_codes=recovery_codes or [],
            last_password_change=now,
        ),
        profile=UserProfile(
            user_id=uid,
            given_name="MFA",
            family_name="User",
            preferred_username="mfauser",
        ),
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.app_name = "Test Identity"
    return settings


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Create mock user repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock(side_effect=lambda u: u)
    return repo


@pytest.fixture
def mock_password_service() -> MagicMock:
    """Create mock password service."""
    svc = MagicMock()
    svc.verify_password = MagicMock(return_value=True)
    return svc


@pytest.fixture
def mock_jwt_service() -> MagicMock:
    """Create mock JWT service."""
    svc = MagicMock()
    svc.decode_token = MagicMock(return_value=None)
    return svc


@pytest.fixture
def mfa_service(
    mock_settings, mock_user_repo, mock_password_service, mock_jwt_service
) -> MFAService:
    """Create MFAService with mocked dependencies."""
    return MFAService(
        settings=mock_settings,
        user_repository=mock_user_repo,
        password_service=mock_password_service,
        jwt_service=mock_jwt_service,
    )


# =============================================================================
# Setup Tests
# =============================================================================


class TestMFASetup:
    """Tests for MFA setup."""

    @pytest.mark.unit
    async def test_setup_success(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Successful MFA setup generates secret, URI, and recovery codes."""
        user = _make_user()
        mock_user_repo.get_by_id.return_value = user

        secret, uri, codes = await mfa_service.setup_mfa(user.id)

        assert secret is not None
        assert uri is not None
        assert "otpauth://" in uri
        assert codes is not None
        assert len(codes) == 10
        mock_user_repo.update.assert_awaited_once()

    @pytest.mark.unit
    async def test_setup_already_enabled(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Setup fails if MFA is already enabled."""
        user = _make_user(mfa_enabled=True, mfa_secret="JBSWY3DPEHPK3PXP")
        mock_user_repo.get_by_id.return_value = user

        secret, uri, codes = await mfa_service.setup_mfa(user.id)

        assert secret is None
        assert uri is None
        assert codes is None

    @pytest.mark.unit
    async def test_setup_user_not_found(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Setup fails if user not found."""
        mock_user_repo.get_by_id.return_value = None

        secret, uri, codes = await mfa_service.setup_mfa(uuid4())

        assert secret is None


# =============================================================================
# Verify and Enable Tests
# =============================================================================


class TestMFAVerifyAndEnable:
    """Tests for MFA verification and enabling."""

    @pytest.mark.unit
    async def test_verify_and_enable_success(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Valid TOTP code enables MFA."""
        secret = pyotp.random_base32()
        user = _make_user(mfa_enabled=False, mfa_secret=secret)
        mock_user_repo.get_by_id.return_value = user

        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        success, error = await mfa_service.verify_and_enable(user.id, valid_code)

        assert success is True
        assert error is None
        assert user.credential.mfa_enabled is True

    @pytest.mark.unit
    async def test_verify_and_enable_invalid_code(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Invalid TOTP code does not enable MFA."""
        secret = pyotp.random_base32()
        user = _make_user(mfa_enabled=False, mfa_secret=secret)
        mock_user_repo.get_by_id.return_value = user

        success, error = await mfa_service.verify_and_enable(user.id, "000000")

        assert success is False
        assert error is not None
        assert user.credential.mfa_enabled is False

    @pytest.mark.unit
    async def test_verify_already_enabled(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Verification fails if MFA is already enabled."""
        user = _make_user(mfa_enabled=True, mfa_secret="JBSWY3DPEHPK3PXP")
        mock_user_repo.get_by_id.return_value = user

        success, error = await mfa_service.verify_and_enable(user.id, "123456")

        assert success is False
        assert "already enabled" in error.lower()

    @pytest.mark.unit
    async def test_verify_no_secret(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Verification fails if setup wasn't initiated."""
        user = _make_user(mfa_enabled=False, mfa_secret=None)
        mock_user_repo.get_by_id.return_value = user

        success, error = await mfa_service.verify_and_enable(user.id, "123456")

        assert success is False
        assert "setup" in error.lower()


# =============================================================================
# Login Verification Tests
# =============================================================================


class TestMFALoginVerification:
    """Tests for TOTP verification during login."""

    @pytest.mark.unit
    async def test_verify_login_code_success(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Valid TOTP during login returns user ID."""
        secret = pyotp.random_base32()
        user = _make_user(mfa_enabled=True, mfa_secret=secret)

        mock_jwt_service.decode_token.return_value = {
            "sub": str(user.id),
            "type": "mfa",
        }
        mock_user_repo.get_by_id.return_value = user

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        user_id, error = await mfa_service.verify_login_code(
            mfa_token="valid_mfa_token",
            code=valid_code,
        )

        assert user_id == user.id
        assert error is None

    @pytest.mark.unit
    async def test_verify_login_code_invalid_token(
        self,
        mfa_service: MFAService,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Invalid MFA token returns error."""
        mock_jwt_service.decode_token.return_value = None

        user_id, error = await mfa_service.verify_login_code(
            mfa_token="expired_token",
            code="123456",
        )

        assert user_id is None
        assert "Invalid" in error

    @pytest.mark.unit
    async def test_verify_login_code_wrong_type(
        self,
        mfa_service: MFAService,
        mock_jwt_service: MagicMock,
    ) -> None:
        """MFA token with wrong type returns error."""
        mock_jwt_service.decode_token.return_value = {
            "sub": str(uuid4()),
            "type": "access",  # Wrong type
        }

        user_id, error = await mfa_service.verify_login_code(
            mfa_token="wrong_type_token",
            code="123456",
        )

        assert user_id is None
        assert error is not None

    @pytest.mark.unit
    async def test_verify_login_code_invalid_totp(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Wrong TOTP code during login returns error."""
        secret = pyotp.random_base32()
        user = _make_user(mfa_enabled=True, mfa_secret=secret)

        mock_jwt_service.decode_token.return_value = {
            "sub": str(user.id),
            "type": "mfa",
        }
        mock_user_repo.get_by_id.return_value = user

        user_id, error = await mfa_service.verify_login_code(
            mfa_token="valid_token",
            code="000000",
        )

        assert user_id is None
        assert "Invalid" in error


# =============================================================================
# Recovery Code Tests
# =============================================================================


class TestMFARecovery:
    """Tests for recovery code usage."""

    @pytest.mark.unit
    async def test_recovery_code_success(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Valid recovery code succeeds and is consumed."""
        codes = ["AAAA1111", "BBBB2222", "CCCC3333"]
        user = _make_user(
            mfa_enabled=True,
            mfa_secret="JBSWY3DPEHPK3PXP",
            recovery_codes=codes.copy(),
        )
        mock_jwt_service.decode_token.return_value = {
            "sub": str(user.id),
            "type": "mfa",
        }
        mock_user_repo.get_by_id.return_value = user

        user_id, remaining, error = await mfa_service.verify_recovery_code(
            mfa_token="valid_token",
            recovery_code="BBBB2222",
        )

        assert user_id == user.id
        assert remaining == 2
        assert error is None
        # Verify code was consumed
        assert "BBBB2222" not in user.credential.recovery_codes

    @pytest.mark.unit
    async def test_recovery_code_invalid(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Invalid recovery code returns error."""
        user = _make_user(
            mfa_enabled=True,
            mfa_secret="JBSWY3DPEHPK3PXP",
            recovery_codes=["AAAA1111"],
        )
        mock_jwt_service.decode_token.return_value = {
            "sub": str(user.id),
            "type": "mfa",
        }
        mock_user_repo.get_by_id.return_value = user

        user_id, remaining, error = await mfa_service.verify_recovery_code(
            mfa_token="valid_token",
            recovery_code="WRONG_CODE",
        )

        assert user_id is None
        assert error is not None


# =============================================================================
# Disable Tests
# =============================================================================


class TestMFADisable:
    """Tests for disabling MFA."""

    @pytest.mark.unit
    async def test_disable_success(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
    ) -> None:
        """Successful MFA disable with valid password and TOTP."""
        secret = pyotp.random_base32()
        user = _make_user(mfa_enabled=True, mfa_secret=secret)
        mock_user_repo.get_by_id.return_value = user

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        success, error = await mfa_service.disable_mfa(
            user_id=user.id,
            password="correct_pw",
            code=valid_code,
        )

        assert success is True
        assert error is None
        assert user.credential.mfa_enabled is False
        assert user.credential.mfa_secret is None

    @pytest.mark.unit
    async def test_disable_wrong_password(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Disable MFA fails with wrong password."""
        user = _make_user(mfa_enabled=True, mfa_secret="JBSWY3DPEHPK3PXP")
        mock_user_repo.get_by_id.return_value = user
        mock_password_service.verify_password.return_value = False

        success, error = await mfa_service.disable_mfa(
            user_id=user.id,
            password="wrong_pw",
            code="123456",
        )

        assert success is False
        assert "password" in error.lower()

    @pytest.mark.unit
    async def test_disable_not_enabled(
        self,
        mfa_service: MFAService,
        mock_user_repo: AsyncMock,
    ) -> None:
        """Disable MFA fails if not enabled."""
        user = _make_user(mfa_enabled=False)
        mock_user_repo.get_by_id.return_value = user

        success, error = await mfa_service.disable_mfa(
            user_id=user.id,
            password="any",
            code="123456",
        )

        assert success is False
        assert "not enabled" in error.lower()


# =============================================================================
# Status Tests
# =============================================================================


class TestMFAStatus:
    """Tests for MFA status check."""

    @pytest.mark.unit
    async def test_status_enabled(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Status returns enabled with recovery code count."""
        user = _make_user(
            mfa_enabled=True,
            mfa_secret="SECRET",
            recovery_codes=["A", "B", "C"],
        )
        mock_user_repo.get_by_id.return_value = user

        enabled, remaining = await mfa_service.get_mfa_status(user.id)

        assert enabled is True
        assert remaining == 3

    @pytest.mark.unit
    async def test_status_disabled(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Status returns disabled for user without MFA."""
        user = _make_user(mfa_enabled=False)
        mock_user_repo.get_by_id.return_value = user

        enabled, remaining = await mfa_service.get_mfa_status(user.id)

        assert enabled is False
        assert remaining == 0

    @pytest.mark.unit
    async def test_status_user_not_found(
        self, mfa_service: MFAService, mock_user_repo: AsyncMock
    ) -> None:
        """Status returns disabled for non-existent user."""
        mock_user_repo.get_by_id.return_value = None

        enabled, remaining = await mfa_service.get_mfa_status(uuid4())

        assert enabled is False
        assert remaining == 0
