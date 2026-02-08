"""Unit tests for UserAuthService."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from identity_service.application.services.user_auth_service import UserAuthService
from identity_service.domain.entities.password_reset import PasswordResetToken
from identity_service.domain.entities.user import User, UserCredential, UserProfile

# =============================================================================
# Fixtures
# =============================================================================


@dataclass
class FakePolicyResult:
    """Fake password policy result."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)


@dataclass
class FakeAccountStatus:
    """Fake account lock status."""

    is_locked: bool = False
    unlock_at: datetime | None = None
    required_delay_seconds: int = 0


@dataclass
class FakeIPStatus:
    """Fake IP status."""

    is_blocked: bool = False


@dataclass
class FakeSessionResult:
    """Fake session creation result."""

    session_id: str = "test-session-123"


def _make_user(
    email: str = "user@example.com",
    username: str = "testuser",
    password_hash: str = "hashed_pw",
    mfa_enabled: bool = False,
    mfa_secret: str | None = None,
    is_active: bool = True,
) -> User:
    """Create a test user entity."""
    uid = uuid4()
    now = datetime.now(UTC)
    return User(
        id=uid,
        email=email,
        username=username,
        is_active=is_active,
        created_at=now,
        updated_at=now,
        credential=UserCredential(
            user_id=uid,
            password_hash=password_hash,
            mfa_enabled=mfa_enabled,
            mfa_secret=mfa_secret,
            last_password_change=now,
        ),
        profile=UserProfile(
            user_id=uid,
            given_name="Test",
            family_name="User",
            preferred_username=username,
        ),
    )


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.login_max_attempts = 5
    settings.login_lockout_duration = 900
    settings.app_name = "Test Identity"
    return settings


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Create mock user repository."""
    repo = AsyncMock()
    repo.exists_by_email = AsyncMock(return_value=False)
    repo.exists_by_username = AsyncMock(return_value=False)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda u: u)
    repo.update = AsyncMock(side_effect=lambda u: u)
    return repo


@pytest.fixture
def mock_reset_repo() -> AsyncMock:
    """Create mock password reset repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_token = AsyncMock(return_value=None)
    repo.mark_as_used = AsyncMock()
    repo.delete_for_user = AsyncMock()
    repo.delete_expired = AsyncMock()
    return repo


@pytest.fixture
def mock_password_service() -> MagicMock:
    """Create mock password service."""
    svc = MagicMock()
    svc.hash_password = MagicMock(return_value="hashed_new_pw")
    svc.verify_password = MagicMock(return_value=True)
    return svc


@pytest.fixture
def mock_password_policy() -> MagicMock:
    """Create mock password policy service."""
    svc = MagicMock()
    svc.validate_password = MagicMock(return_value=FakePolicyResult(is_valid=True))
    return svc


@pytest.fixture
def mock_brute_force() -> MagicMock:
    """Create mock brute force protection service."""
    svc = MagicMock()
    svc.check_account = MagicMock(return_value=FakeAccountStatus())
    svc.check_ip = MagicMock(return_value=FakeIPStatus())
    svc.record_attempt = MagicMock()
    return svc


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Create mock session management service."""
    svc = MagicMock()
    svc.create_session = MagicMock(return_value=FakeSessionResult())
    return svc


@pytest.fixture
def mock_jwt_service() -> MagicMock:
    """Create mock JWT service."""
    svc = MagicMock()
    svc.create_access_token = MagicMock(return_value=("access_token_value", "jti_123", 3600))
    svc.create_id_token = MagicMock(return_value="id_token_value")
    svc.create_mfa_token = MagicMock(return_value="mfa_token_value")
    svc.decode_token = MagicMock(return_value=None)
    return svc


@pytest.fixture
def auth_service(
    mock_settings,
    mock_user_repo,
    mock_reset_repo,
    mock_password_service,
    mock_password_policy,
    mock_brute_force,
    mock_session_service,
    mock_jwt_service,
) -> UserAuthService:
    """Create UserAuthService with all mocked dependencies."""
    return UserAuthService(
        settings=mock_settings,
        user_repository=mock_user_repo,
        password_reset_repository=mock_reset_repo,
        password_service=mock_password_service,
        password_policy_service=mock_password_policy,
        brute_force_service=mock_brute_force,
        session_service=mock_session_service,
        jwt_service=mock_jwt_service,
    )


# =============================================================================
# Registration Tests
# =============================================================================


class TestRegister:
    """Tests for user registration."""

    @pytest.mark.unit
    async def test_register_success(
        self, auth_service: UserAuthService, mock_user_repo: AsyncMock
    ) -> None:
        """Registration with valid data returns success."""
        result = await auth_service.register(
            email="new@example.com",
            password="StrongPassword123!",
            username="newuser",
            given_name="New",
            family_name="User",
        )

        assert result.success is True
        assert result.user_id is not None
        assert result.error is None
        mock_user_repo.create.assert_awaited_once()

    @pytest.mark.unit
    async def test_register_duplicate_email(
        self, auth_service: UserAuthService, mock_user_repo: AsyncMock
    ) -> None:
        """Registration with existing email returns error."""
        mock_user_repo.exists_by_email.return_value = True

        result = await auth_service.register(
            email="exists@example.com",
            password="StrongPassword123!",
        )

        assert result.success is False
        assert result.error == "email_exists"
        mock_user_repo.create.assert_not_awaited()

    @pytest.mark.unit
    async def test_register_duplicate_username(
        self, auth_service: UserAuthService, mock_user_repo: AsyncMock
    ) -> None:
        """Registration with existing username returns error."""
        mock_user_repo.exists_by_username.return_value = True

        result = await auth_service.register(
            email="new@example.com",
            password="StrongPassword123!",
            username="taken",
        )

        assert result.success is False
        assert result.error == "username_exists"

    @pytest.mark.unit
    async def test_register_weak_password(
        self, auth_service: UserAuthService, mock_password_policy: MagicMock
    ) -> None:
        """Registration with weak password returns errors."""
        mock_password_policy.validate_password.return_value = FakePolicyResult(
            is_valid=False, errors=["Password too short"]
        )

        result = await auth_service.register(
            email="new@example.com",
            password="weak",
        )

        assert result.success is False
        assert result.error == "weak_password"
        assert "Password too short" in result.errors

    @pytest.mark.unit
    async def test_register_hashes_password(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Registration hashes the password before storage."""
        await auth_service.register(
            email="new@example.com",
            password="StrongPassword123!",
        )

        mock_password_service.hash_password.assert_called_once_with("StrongPassword123!")
        # Verify the created user has the hashed password
        created_user = mock_user_repo.create.call_args[0][0]
        assert created_user.credential.password_hash == "hashed_new_pw"


# =============================================================================
# Login Tests
# =============================================================================


class TestLogin:
    """Tests for user login."""

    @pytest.mark.unit
    async def test_login_success(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_brute_force: MagicMock,
    ) -> None:
        """Successful login with valid credentials."""
        user = _make_user()
        mock_user_repo.get_by_email.return_value = user

        result = await auth_service.login(
            email="user@example.com",
            password="correct_password",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.success is True
        assert result.session_id is not None
        mock_brute_force.record_attempt.assert_called()

    @pytest.mark.unit
    async def test_login_account_locked(
        self,
        auth_service: UserAuthService,
        mock_brute_force: MagicMock,
    ) -> None:
        """Login on locked account returns error."""
        mock_brute_force.check_account.return_value = FakeAccountStatus(
            is_locked=True,
            unlock_at=datetime.now(UTC),
        )

        result = await auth_service.login(
            email="locked@example.com",
            password="any_password",
        )

        assert result.success is False
        assert result.error == "account_locked"

    @pytest.mark.unit
    async def test_login_ip_blocked(
        self,
        auth_service: UserAuthService,
        mock_brute_force: MagicMock,
    ) -> None:
        """Login from blocked IP returns error."""
        mock_brute_force.check_ip.return_value = FakeIPStatus(is_blocked=True)

        result = await auth_service.login(
            email="user@example.com",
            password="any_password",
            ip_address="1.2.3.4",
        )

        assert result.success is False
        assert result.error == "ip_blocked"

    @pytest.mark.unit
    async def test_login_user_not_found(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_brute_force: MagicMock,
    ) -> None:
        """Login with unknown email returns invalid_credentials."""
        mock_user_repo.get_by_email.return_value = None

        result = await auth_service.login(
            email="unknown@example.com",
            password="any_password",
            ip_address="127.0.0.1",
        )

        assert result.success is False
        assert result.error == "invalid_credentials"
        mock_brute_force.record_attempt.assert_called_once()

    @pytest.mark.unit
    async def test_login_wrong_password(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
        mock_brute_force: MagicMock,
    ) -> None:
        """Login with wrong password returns error and records attempt."""
        user = _make_user()
        mock_user_repo.get_by_email.return_value = user
        mock_password_service.verify_password.return_value = False

        result = await auth_service.login(
            email="user@example.com",
            password="wrong_password",
            ip_address="127.0.0.1",
        )

        assert result.success is False
        assert result.error == "invalid_credentials"
        # Should record a failed attempt
        mock_brute_force.record_attempt.assert_called_once()

    @pytest.mark.unit
    async def test_login_mfa_required(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_jwt_service: MagicMock,
    ) -> None:
        """Login with MFA enabled returns MFA challenge."""
        user = _make_user(mfa_enabled=True, mfa_secret="JBSWY3DPEHPK3PXP")
        mock_user_repo.get_by_email.return_value = user

        result = await auth_service.login(
            email="user@example.com",
            password="correct_password",
        )

        assert result.success is False
        assert result.requires_mfa is True
        assert result.mfa_token == "mfa_token_value"
        mock_jwt_service.create_mfa_token.assert_called_once()

    @pytest.mark.unit
    async def test_login_inactive_user(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
    ) -> None:
        """Login with inactive account returns error."""
        user = _make_user(is_active=False)
        mock_user_repo.get_by_email.return_value = user

        result = await auth_service.login(
            email="user@example.com",
            password="correct_password",
        )

        assert result.success is False


# =============================================================================
# Password Change Tests
# =============================================================================


class TestChangePassword:
    """Tests for password change."""

    @pytest.mark.unit
    async def test_change_password_success(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Successful password change."""
        user = _make_user()
        mock_user_repo.get_by_id.return_value = user
        # verify_password: True for current, False for new (not same as current)
        mock_password_service.verify_password.side_effect = [True, False]

        with patch(
            "identity_service.infrastructure.security.password_policy.add_to_password_history"
        ):
            success, error = await auth_service.change_password(
                user_id=user.id,
                current_password="current_pw",
                new_password="NewStrongPw123!",
            )

        assert success is True
        assert error is None
        mock_user_repo.update.assert_awaited_once()

    @pytest.mark.unit
    async def test_change_password_wrong_current(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Password change with wrong current password fails."""
        user = _make_user()
        mock_user_repo.get_by_id.return_value = user
        mock_password_service.verify_password.return_value = False

        success, error = await auth_service.change_password(
            user_id=user.id,
            current_password="wrong_pw",
            new_password="NewStrongPw123!",
        )

        assert success is False
        assert error == "Current password is incorrect"

    @pytest.mark.unit
    async def test_change_password_user_not_found(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
    ) -> None:
        """Password change for non-existent user fails."""
        mock_user_repo.get_by_id.return_value = None

        success, error = await auth_service.change_password(
            user_id=uuid4(),
            current_password="any",
            new_password="any",
        )

        assert success is False
        assert error == "User not found"

    @pytest.mark.unit
    async def test_change_password_same_as_current(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Password change to same password fails."""
        user = _make_user()
        mock_user_repo.get_by_id.return_value = user
        # Both verify calls return True (current matches, new also matches old hash)
        mock_password_service.verify_password.return_value = True

        success, error = await auth_service.change_password(
            user_id=user.id,
            current_password="same_pw",
            new_password="same_pw",
        )

        assert success is False
        assert "different" in error.lower()


# =============================================================================
# Password Reset Tests
# =============================================================================


class TestPasswordReset:
    """Tests for password reset flow."""

    @pytest.mark.unit
    async def test_request_reset_existing_user(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_reset_repo: AsyncMock,
    ) -> None:
        """Password reset request for existing user creates token."""
        user = _make_user()
        mock_user_repo.get_by_email.return_value = user

        token = await auth_service.request_password_reset(
            email="user@example.com",
            ip_address="127.0.0.1",
        )

        assert token is not None
        mock_reset_repo.delete_for_user.assert_awaited_once()
        mock_reset_repo.save.assert_awaited_once()

    @pytest.mark.unit
    async def test_request_reset_unknown_email(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_reset_repo: AsyncMock,
    ) -> None:
        """Password reset request for unknown email returns None (no enumeration)."""
        mock_user_repo.get_by_email.return_value = None

        token = await auth_service.request_password_reset(
            email="unknown@example.com",
        )

        assert token is None
        mock_reset_repo.save.assert_not_awaited()

    @pytest.mark.unit
    async def test_reset_password_success(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_reset_repo: AsyncMock,
    ) -> None:
        """Successful password reset with valid token."""
        user = _make_user()
        reset_token = PasswordResetToken(
            user_id=user.id,
            email="user@example.com",
        )
        mock_reset_repo.get_by_token.return_value = reset_token
        mock_user_repo.get_by_id.return_value = user

        with patch(
            "identity_service.infrastructure.security.password_policy.add_to_password_history"
        ):
            success, error = await auth_service.reset_password(
                token=reset_token.token,
                new_password="NewStrongPw123!",
            )

        assert success is True
        assert error is None
        mock_reset_repo.mark_as_used.assert_awaited_once()

    @pytest.mark.unit
    async def test_reset_password_invalid_token(
        self,
        auth_service: UserAuthService,
        mock_reset_repo: AsyncMock,
    ) -> None:
        """Password reset with invalid token fails."""
        mock_reset_repo.get_by_token.return_value = None

        success, error = await auth_service.reset_password(
            token="invalid_token",
            new_password="NewStrongPw123!",
        )

        assert success is False
        assert "Invalid" in error or "expired" in error

    @pytest.mark.unit
    async def test_reset_password_weak_password(
        self,
        auth_service: UserAuthService,
        mock_user_repo: AsyncMock,
        mock_reset_repo: AsyncMock,
        mock_password_policy: MagicMock,
    ) -> None:
        """Password reset with weak password fails."""
        user = _make_user()
        reset_token = PasswordResetToken(user_id=user.id, email="user@example.com")
        mock_reset_repo.get_by_token.return_value = reset_token
        mock_user_repo.get_by_id.return_value = user
        mock_password_policy.validate_password.return_value = FakePolicyResult(
            is_valid=False, errors=["Too short"]
        )

        success, error = await auth_service.reset_password(
            token=reset_token.token,
            new_password="weak",
        )

        assert success is False
        assert "Too short" in error
