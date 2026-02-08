"""Password reset token domain entity."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from shared.utils import now_utc


@dataclass
class PasswordResetToken:
    """Token for password reset flow.

    Generated when user requests password reset, consumed when
    user provides new password with valid token.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    email: str = ""
    expires_at: datetime = field(default_factory=lambda: now_utc() + timedelta(hours=1))
    is_used: bool = False
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)
    ip_address: str | None = None

    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not used)."""
        if self.is_used:
            return False
        return now_utc() < self.expires_at

    def consume(self) -> None:
        """Mark token as used."""
        self.is_used = True
        self.used_at = now_utc()
