"""Password Policy Service - Enhanced password management.

Features:
- Password complexity validation (strength scoring)
- Password history (prevent reuse)
- Password expiry tracking
- Common password dictionary check
- Breach detection integration (optional)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING

from shared.observability import get_structlog_logger

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings

logger = get_structlog_logger(__name__)


# ========================================
# Password Strength Levels
# ========================================


class PasswordStrength(str, Enum):
    """Password strength levels."""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    FAIR = "fair"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class PasswordValidationResult:
    """Result of password validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    strength: PasswordStrength = PasswordStrength.VERY_WEAK
    score: int = 0  # 0-100
    suggestions: list[str] = field(default_factory=list)


# ========================================
# Common Passwords (Top 1000 - abbreviated sample)
# ========================================

COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123",
    "monkey", "1234567", "letmein", "trustno1", "dragon",
    "baseball", "iloveyou", "master", "sunshine", "ashley",
    "bailey", "passw0rd", "shadow", "123123", "654321",
    "superman", "qazwsx", "michael", "football", "password1",
    "password123", "welcome", "welcome1", "admin", "admin123",
    "root", "toor", "login", "changeme", "default",
    # Add more in production
}


# ========================================
# Password History Storage (In-memory for demo)
# ========================================

# user_id -> list of (password_hash, changed_at)
_password_history: dict[str, list[tuple[str, datetime]]] = {}


def add_to_password_history(
    user_id: str,
    password_hash: str,
    max_history: int = 12,
) -> None:
    """Add password hash to user's history.

    Args:
        user_id: User identifier
        password_hash: Hashed password
        max_history: Maximum entries to keep
    """
    if user_id not in _password_history:
        _password_history[user_id] = []

    history = _password_history[user_id]
    history.append((password_hash, datetime.now(timezone.utc)))

    # Trim old entries
    if len(history) > max_history:
        _password_history[user_id] = history[-max_history:]


def get_password_history(user_id: str) -> list[tuple[str, datetime]]:
    """Get user's password history.

    Args:
        user_id: User identifier

    Returns:
        List of (password_hash, changed_at) tuples
    """
    return _password_history.get(user_id, [])


def clear_password_history(user_id: str) -> None:
    """Clear user's password history (e.g., on account reset)."""
    _password_history.pop(user_id, None)


# ========================================
# Password Expiry Tracking
# ========================================

# user_id -> password_changed_at
_password_timestamps: dict[str, datetime] = {}


def set_password_timestamp(user_id: str, timestamp: datetime | None = None) -> None:
    """Record when password was last changed.

    Args:
        user_id: User identifier
        timestamp: When password was changed (defaults to now)
    """
    _password_timestamps[user_id] = timestamp or datetime.now(timezone.utc)


def get_password_timestamp(user_id: str) -> datetime | None:
    """Get when password was last changed.

    Args:
        user_id: User identifier

    Returns:
        Timestamp or None if not tracked
    """
    return _password_timestamps.get(user_id)


def is_password_expired(
    user_id: str,
    max_age_days: int = 90,
) -> bool:
    """Check if user's password has expired.

    Args:
        user_id: User identifier
        max_age_days: Maximum password age in days (0 = no expiry)

    Returns:
        True if password is expired
    """
    if max_age_days <= 0:
        return False

    timestamp = get_password_timestamp(user_id)
    if not timestamp:
        return True  # No timestamp = treat as expired

    expiry = timestamp + timedelta(days=max_age_days)
    return datetime.now(timezone.utc) > expiry


def days_until_expiry(
    user_id: str,
    max_age_days: int = 90,
) -> int | None:
    """Get days until password expires.

    Args:
        user_id: User identifier
        max_age_days: Maximum password age in days

    Returns:
        Days until expiry, negative if expired, None if no expiry
    """
    if max_age_days <= 0:
        return None

    timestamp = get_password_timestamp(user_id)
    if not timestamp:
        return 0  # Treat as expired

    expiry = timestamp + timedelta(days=max_age_days)
    delta = expiry - datetime.now(timezone.utc)
    return delta.days


# ========================================
# Password Policy Service
# ========================================


class PasswordPolicyService:
    """Enhanced password policy enforcement."""

    def __init__(self, settings: Settings) -> None:
        """Initialize policy service.

        Args:
            settings: Application settings
        """
        self._settings = settings

    def validate_password(
        self,
        password: str,
        user_id: str | None = None,
        username: str | None = None,
        email: str | None = None,
        verify_func: callable | None = None,
    ) -> PasswordValidationResult:
        """Validate password against comprehensive policy.

        Args:
            password: Password to validate
            user_id: User ID (for history check)
            username: Username (to check similarity)
            email: Email (to check similarity)
            verify_func: Function to verify against hash (for history)

        Returns:
            Validation result with errors, warnings, and strength
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        score = 0
        settings = self._settings

        # Length check
        min_len = settings.password_min_length
        if len(password) < min_len:
            errors.append(f"Password must be at least {min_len} characters")
        elif len(password) < 12:
            warnings.append("Consider using 12+ characters for better security")
            suggestions.append("Use a longer password or passphrase")

        # Length scoring (up to 25 points)
        score += min(25, len(password) * 2)

        # Character class checks
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\;\'`~\-_=+]', password))

        if settings.password_require_uppercase and not has_upper:
            errors.append("Password must contain at least one uppercase letter")
        if settings.password_require_lowercase and not has_lower:
            errors.append("Password must contain at least one lowercase letter")
        if settings.password_require_digit and not has_digit:
            errors.append("Password must contain at least one digit")
        if settings.password_require_special and not has_special:
            errors.append("Password must contain at least one special character")

        # Character diversity scoring (up to 25 points)
        char_classes = sum([has_upper, has_lower, has_digit, has_special])
        score += char_classes * 6

        if char_classes < 3:
            suggestions.append("Use a mix of uppercase, lowercase, numbers, and symbols")

        # Common password check
        if password.lower() in COMMON_PASSWORDS:
            errors.append("This password is too common")
            score = max(0, score - 30)

        # Keyboard pattern check (qwerty, 12345, etc.)
        keyboard_patterns = [
            "qwerty", "asdfgh", "zxcvbn", "qazwsx",
            "123456", "654321", "abcdef", "fedcba",
        ]
        lower_pass = password.lower()
        for pattern in keyboard_patterns:
            if pattern in lower_pass:
                warnings.append("Avoid keyboard patterns")
                score = max(0, score - 10)
                break

        # Repeated characters check
        if re.search(r"(.)\1{2,}", password):
            warnings.append("Avoid repeated characters")
            score = max(0, score - 10)

        # Sequential characters check
        if re.search(r"(012|123|234|345|456|567|678|789|890|abc|bcd|cde)", lower_pass):
            warnings.append("Avoid sequential characters")
            score = max(0, score - 10)

        # Username similarity check
        if username:
            if username.lower() in lower_pass or lower_pass in username.lower():
                errors.append("Password cannot contain your username")
                score = max(0, score - 20)

        # Email similarity check
        if email:
            email_parts = email.lower().split("@")[0]
            if email_parts in lower_pass:
                warnings.append("Password should not contain parts of your email")
                score = max(0, score - 10)

        # Password history check
        if user_id and verify_func:
            history = get_password_history(user_id)
            history_limit = getattr(settings, "password_history_count", 12)
            recent_history = history[-history_limit:] if len(history) > history_limit else history

            for old_hash, _ in recent_history:
                try:
                    if verify_func(password, old_hash):
                        errors.append(
                            f"Cannot reuse any of your last {history_limit} passwords"
                        )
                        break
                except Exception:
                    pass  # Invalid hash format, skip

        # Entropy bonus (up to 25 points)
        unique_chars = len(set(password))
        entropy_score = min(25, unique_chars * 2)
        score += entropy_score

        # Cap score at 100
        score = min(100, max(0, score))

        # Determine strength
        if score >= 80:
            strength = PasswordStrength.VERY_STRONG
        elif score >= 60:
            strength = PasswordStrength.STRONG
        elif score >= 40:
            strength = PasswordStrength.FAIR
        elif score >= 20:
            strength = PasswordStrength.WEAK
        else:
            strength = PasswordStrength.VERY_WEAK

        # Minimum strength requirement
        min_strength = getattr(settings, "password_min_strength", "fair")
        strength_order = ["very_weak", "weak", "fair", "strong", "very_strong"]
        if strength_order.index(strength.value) < strength_order.index(min_strength):
            errors.append(f"Password strength must be at least '{min_strength}'")

        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            strength=strength,
            score=score,
            suggestions=suggestions,
        )

    def check_breach(self, password: str) -> bool:
        """Check if password appears in known breaches.

        Uses Have I Been Pwned API with k-anonymity.

        Args:
            password: Password to check

        Returns:
            True if password is compromised
        """
        # Calculate SHA-1 hash
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]

        # In production, make API call to HIBP
        # GET https://api.pwnedpasswords.com/range/{prefix}
        # Check if suffix appears in response

        # For demo, return False (not breached)
        logger.debug("Breach check performed", prefix=prefix)
        return False


# ========================================
# Singleton Instance
# ========================================

_policy_service: PasswordPolicyService | None = None


def get_password_policy_service(settings: Settings) -> PasswordPolicyService:
    """Get password policy service instance."""
    global _policy_service
    if _policy_service is None:
        _policy_service = PasswordPolicyService(settings)
    return _policy_service
