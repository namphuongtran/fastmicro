"""Tests for shared.auth.password module.

This module tests password hashing and verification using Argon2.
"""

from __future__ import annotations

import pytest

from shared.auth.password import (
    PasswordService,
    PasswordStrengthError,
    check_password_strength,
)


class TestPasswordService:
    """Tests for PasswordService class."""

    @pytest.fixture
    def password_service(self) -> PasswordService:
        """Create password service instance."""
        return PasswordService()

    def test_hash_password(self, password_service: PasswordService) -> None:
        """Should hash password."""
        hashed = password_service.hash("mypassword123")

        assert isinstance(hashed, str)
        assert hashed != "mypassword123"
        assert hashed.startswith("$argon2")

    def test_hash_produces_different_hashes(self, password_service: PasswordService) -> None:
        """Should produce different hashes for same password (salting)."""
        hash1 = password_service.hash("mypassword123")
        hash2 = password_service.hash("mypassword123")

        assert hash1 != hash2

    def test_verify_correct_password(self, password_service: PasswordService) -> None:
        """Should verify correct password."""
        hashed = password_service.hash("mypassword123")

        assert password_service.verify("mypassword123", hashed) is True

    def test_verify_incorrect_password(self, password_service: PasswordService) -> None:
        """Should reject incorrect password."""
        hashed = password_service.hash("mypassword123")

        assert password_service.verify("wrongpassword", hashed) is False

    def test_verify_empty_password(self, password_service: PasswordService) -> None:
        """Should reject empty password."""
        hashed = password_service.hash("mypassword123")

        assert password_service.verify("", hashed) is False

    def test_verify_invalid_hash(self, password_service: PasswordService) -> None:
        """Should return False for invalid hash format."""
        assert password_service.verify("password", "invalid-hash") is False

    def test_needs_rehash_false(self, password_service: PasswordService) -> None:
        """Should not need rehash for fresh hash."""
        hashed = password_service.hash("mypassword123")

        assert password_service.needs_rehash(hashed) is False

    def test_needs_rehash_old_parameters(self) -> None:
        """Should need rehash for hash with outdated parameters."""
        # Create service with different parameters
        old_service = PasswordService(
            time_cost=1,
            memory_cost=32768,
            parallelism=1,
        )
        new_service = PasswordService(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
        )

        old_hash = old_service.hash("mypassword123")

        # New service should detect old hash needs rehashing
        assert new_service.needs_rehash(old_hash) is True

    def test_hash_with_custom_parameters(self) -> None:
        """Should support custom Argon2 parameters."""
        service = PasswordService(
            time_cost=4,
            memory_cost=131072,
            parallelism=8,
        )

        hashed = service.hash("mypassword123")
        assert service.verify("mypassword123", hashed) is True


class TestCheckPasswordStrength:
    """Tests for check_password_strength function."""

    def test_strong_password(self) -> None:
        """Should accept strong password."""
        # Should not raise
        check_password_strength("MyStr0ng!Pass#2024")

    def test_password_too_short(self) -> None:
        """Should reject password that is too short."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength("Short1!", min_length=8)

        assert "at least 8 characters" in str(exc_info.value)

    def test_password_no_uppercase(self) -> None:
        """Should reject password without uppercase."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength(
                "mypassword123!",
                require_uppercase=True,
            )

        assert "uppercase" in str(exc_info.value).lower()

    def test_password_no_lowercase(self) -> None:
        """Should reject password without lowercase."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength(
                "MYPASSWORD123!",
                require_lowercase=True,
            )

        assert "lowercase" in str(exc_info.value).lower()

    def test_password_no_digit(self) -> None:
        """Should reject password without digit."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength(
                "MyPassword!",
                require_digit=True,
            )

        assert "digit" in str(exc_info.value).lower()

    def test_password_no_special(self) -> None:
        """Should reject password without special character."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength(
                "MyPassword123",
                require_special=True,
            )

        assert "special" in str(exc_info.value).lower()

    def test_custom_min_length(self) -> None:
        """Should support custom minimum length."""
        # Should not raise with 12+ chars
        check_password_strength("MyPassword12!", min_length=12)

        # Should raise with less than 12 chars
        with pytest.raises(PasswordStrengthError):
            check_password_strength("MyPass1!", min_length=12)

    def test_default_requirements(self) -> None:
        """Should use sensible default requirements."""
        # Should accept password meeting basic requirements
        check_password_strength("Password123")

        # Should reject password that's too short
        with pytest.raises(PasswordStrengthError):
            check_password_strength("Pass1")


class TestPasswordStrengthError:
    """Tests for PasswordStrengthError exception."""

    def test_password_strength_error(self) -> None:
        """Should create password strength error."""
        error = PasswordStrengthError("Password too weak")

        assert str(error) == "Password too weak"
        assert isinstance(error, ValueError)

    def test_password_strength_error_with_requirements(self) -> None:
        """Should include failed requirements."""
        error = PasswordStrengthError(
            "Password does not meet requirements",
            failed_requirements=["uppercase", "special"],
        )

        assert error.failed_requirements == ["uppercase", "special"]
