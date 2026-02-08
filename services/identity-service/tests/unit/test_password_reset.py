"""Unit tests for PasswordResetToken entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from identity_service.domain.entities.password_reset import PasswordResetToken


class TestPasswordResetToken:
    """Tests for PasswordResetToken entity."""

    @pytest.mark.unit
    def test_create_token(self) -> None:
        """Token is created with valid defaults."""
        user_id = uuid4()
        token = PasswordResetToken(
            user_id=user_id,
            email="test@example.com",
        )

        assert token.user_id == user_id
        assert token.email == "test@example.com"
        assert token.token is not None
        assert len(token.token) > 20
        assert token.is_used is False
        assert token.expires_at > datetime.now(UTC)

    @pytest.mark.unit
    def test_is_valid_fresh_token(self) -> None:
        """Fresh token is valid."""
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
        )

        assert token.is_valid() is True

    @pytest.mark.unit
    def test_is_valid_expired_token(self) -> None:
        """Expired token is not valid."""
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        assert token.is_valid() is False

    @pytest.mark.unit
    def test_is_valid_used_token(self) -> None:
        """Used token is not valid."""
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
        )
        token.consume()

        assert token.is_valid() is False
        assert token.is_used is True

    @pytest.mark.unit
    def test_consume_token(self) -> None:
        """Consuming a token marks it as used with timestamp."""
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
        )

        token.consume()

        assert token.is_used is True
        assert token.used_at is not None

    @pytest.mark.unit
    def test_custom_expiry(self) -> None:
        """Token can be created with custom expiry."""
        custom_expiry = datetime.now(UTC) + timedelta(hours=24)
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
            expires_at=custom_expiry,
        )

        assert token.expires_at == custom_expiry
        assert token.is_valid() is True

    @pytest.mark.unit
    def test_ip_address_stored(self) -> None:
        """IP address is stored with the token."""
        token = PasswordResetToken(
            user_id=uuid4(),
            email="test@example.com",
            ip_address="192.168.1.1",
        )

        assert token.ip_address == "192.168.1.1"

    @pytest.mark.unit
    def test_tokens_are_unique(self) -> None:
        """Each token gets a unique token string."""
        uid = uuid4()
        token1 = PasswordResetToken(user_id=uid, email="test@example.com")
        token2 = PasswordResetToken(user_id=uid, email="test@example.com")

        assert token1.token != token2.token
