"""Brute Force Protection Service.

Features:
- Account lockout after configurable failed attempts
- Progressive delay between attempts
- IP-based rate limiting and blocking
- Distributed tracking support (Redis-ready)
- Automatic unlock after cooldown period
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from shared.observability import get_structlog_logger

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings

logger = get_structlog_logger(__name__)


# ========================================
# Types and Data Classes
# ========================================


class LockoutReason(str, Enum):
    """Reason for account lockout."""

    FAILED_ATTEMPTS = "failed_attempts"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_ACTION = "admin_action"
    IP_BLOCKED = "ip_blocked"


@dataclass
class LoginAttempt:
    """Record of a login attempt."""

    timestamp: datetime
    ip_address: str
    user_agent: str | None
    success: bool
    failure_reason: str | None = None


@dataclass
class AccountLockStatus:
    """Current lock status for an account."""

    is_locked: bool
    reason: LockoutReason | None = None
    locked_at: datetime | None = None
    unlock_at: datetime | None = None
    failed_attempts: int = 0
    last_attempt_at: datetime | None = None
    required_delay_seconds: float = 0


@dataclass
class IPStatus:
    """Status for an IP address."""

    ip_address: str
    is_blocked: bool = False
    blocked_at: datetime | None = None
    blocked_until: datetime | None = None
    failed_attempts: int = 0
    last_attempt_at: datetime | None = None
    suspicious_score: int = 0


@dataclass
class AttemptTracker:
    """Tracks login attempts for a user or IP."""

    attempts: list[LoginAttempt] = field(default_factory=list)
    failed_count: int = 0
    locked: bool = False
    locked_at: datetime | None = None
    locked_until: datetime | None = None
    lock_reason: LockoutReason | None = None


# ========================================
# In-Memory Storage (Replace with Redis in production)
# ========================================

# username -> AttemptTracker
_user_trackers: dict[str, AttemptTracker] = {}

# ip_address -> AttemptTracker
_ip_trackers: dict[str, AttemptTracker] = {}

# Set of permanently blocked IPs
_blocked_ips: set[str] = set()


def _get_user_tracker(username: str) -> AttemptTracker:
    """Get or create tracker for user."""
    if username not in _user_trackers:
        _user_trackers[username] = AttemptTracker()
    return _user_trackers[username]


def _get_ip_tracker(ip_address: str) -> AttemptTracker:
    """Get or create tracker for IP."""
    if ip_address not in _ip_trackers:
        _ip_trackers[ip_address] = AttemptTracker()
    return _ip_trackers[ip_address]


def _cleanup_old_attempts(tracker: AttemptTracker, window_minutes: int = 30) -> None:
    """Remove attempts older than the tracking window."""
    cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)
    tracker.attempts = [a for a in tracker.attempts if a.timestamp > cutoff]

    # Recalculate failed count
    tracker.failed_count = sum(1 for a in tracker.attempts if not a.success)


# ========================================
# Brute Force Protection Service
# ========================================


class BruteForceProtectionService:
    """Service for protecting against brute force attacks."""

    def __init__(self, settings: Settings) -> None:
        """Initialize protection service.

        Args:
            settings: Application settings
        """
        self._settings = settings

        # Default configuration (can be overridden by settings)
        self.max_failed_attempts = getattr(settings, "max_failed_login_attempts", 5)
        self.lockout_duration_minutes = getattr(settings, "account_lockout_duration_minutes", 30)
        self.tracking_window_minutes = getattr(settings, "login_tracking_window_minutes", 30)
        self.progressive_delay_enabled = getattr(settings, "progressive_delay_enabled", True)
        self.ip_max_failed_attempts = getattr(settings, "ip_max_failed_attempts", 20)
        self.ip_block_duration_hours = getattr(settings, "ip_block_duration_hours", 1)

    def check_account(self, username: str) -> AccountLockStatus:
        """Check if account is locked.

        Args:
            username: Username to check

        Returns:
            Current lock status
        """
        tracker = _get_user_tracker(username)
        _cleanup_old_attempts(tracker, self.tracking_window_minutes)

        # Check if lock has expired
        if tracker.locked and tracker.locked_until:
            if datetime.now(UTC) > tracker.locked_until:
                # Auto-unlock
                tracker.locked = False
                tracker.locked_at = None
                tracker.locked_until = None
                tracker.lock_reason = None
                tracker.failed_count = 0
                tracker.attempts.clear()
                logger.info("Account auto-unlocked", username=username)

        # Calculate required delay (progressive)
        required_delay = 0.0
        if self.progressive_delay_enabled and tracker.failed_count > 0:
            # Exponential backoff: 2^(attempts-1) seconds, capped at 30 seconds
            required_delay = min(30, 2 ** (tracker.failed_count - 1))

            # Check if enough time has passed since last attempt
            if tracker.attempts:
                last_attempt = tracker.attempts[-1]
                elapsed = (datetime.now(UTC) - last_attempt.timestamp).total_seconds()
                required_delay = max(0, required_delay - elapsed)

        return AccountLockStatus(
            is_locked=tracker.locked,
            reason=tracker.lock_reason,
            locked_at=tracker.locked_at,
            unlock_at=tracker.locked_until,
            failed_attempts=tracker.failed_count,
            last_attempt_at=tracker.attempts[-1].timestamp if tracker.attempts else None,
            required_delay_seconds=required_delay,
        )

    def check_ip(self, ip_address: str) -> IPStatus:
        """Check if IP address is blocked.

        Args:
            ip_address: IP to check

        Returns:
            Current IP status
        """
        # Check permanent block list
        if ip_address in _blocked_ips:
            return IPStatus(
                ip_address=ip_address,
                is_blocked=True,
                suspicious_score=100,
            )

        tracker = _get_ip_tracker(ip_address)
        _cleanup_old_attempts(tracker, self.tracking_window_minutes)

        # Check if block has expired
        if tracker.locked and tracker.locked_until:
            if datetime.now(UTC) > tracker.locked_until:
                tracker.locked = False
                tracker.locked_at = None
                tracker.locked_until = None
                tracker.failed_count = 0
                logger.info("IP auto-unblocked", ip_address=ip_address)

        # Calculate suspicious score (0-100)
        suspicious_score = min(100, tracker.failed_count * 5)

        return IPStatus(
            ip_address=ip_address,
            is_blocked=tracker.locked,
            blocked_at=tracker.locked_at,
            blocked_until=tracker.locked_until,
            failed_attempts=tracker.failed_count,
            last_attempt_at=tracker.attempts[-1].timestamp if tracker.attempts else None,
            suspicious_score=suspicious_score,
        )

    def record_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool,
        user_agent: str | None = None,
        failure_reason: str | None = None,
    ) -> tuple[AccountLockStatus, IPStatus]:
        """Record a login attempt.

        Args:
            username: Username attempted
            ip_address: Source IP address
            success: Whether login succeeded
            user_agent: Client user agent
            failure_reason: Reason for failure

        Returns:
            Tuple of (account_status, ip_status)
        """
        now = datetime.now(UTC)
        attempt = LoginAttempt(
            timestamp=now,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )

        # Track by username
        user_tracker = _get_user_tracker(username)
        _cleanup_old_attempts(user_tracker, self.tracking_window_minutes)
        user_tracker.attempts.append(attempt)

        # Track by IP
        ip_tracker = _get_ip_tracker(ip_address)
        _cleanup_old_attempts(ip_tracker, self.tracking_window_minutes)
        ip_tracker.attempts.append(attempt)

        if success:
            # Reset failed counts on success
            user_tracker.failed_count = 0
            # Don't reset IP tracker - could be shared IP
            logger.info(
                "Successful login",
                username=username,
                ip_address=ip_address,
            )
        else:
            user_tracker.failed_count += 1
            ip_tracker.failed_count += 1

            logger.warning(
                "Failed login attempt",
                username=username,
                ip_address=ip_address,
                failed_attempts=user_tracker.failed_count,
                reason=failure_reason,
            )

            # Check if account should be locked
            if user_tracker.failed_count >= self.max_failed_attempts:
                user_tracker.locked = True
                user_tracker.locked_at = now
                user_tracker.locked_until = now + timedelta(minutes=self.lockout_duration_minutes)
                user_tracker.lock_reason = LockoutReason.FAILED_ATTEMPTS

                logger.warning(
                    "Account locked due to failed attempts",
                    username=username,
                    locked_until=user_tracker.locked_until.isoformat(),
                )

            # Check if IP should be blocked
            if ip_tracker.failed_count >= self.ip_max_failed_attempts:
                ip_tracker.locked = True
                ip_tracker.locked_at = now
                ip_tracker.locked_until = now + timedelta(hours=self.ip_block_duration_hours)

                logger.warning(
                    "IP blocked due to failed attempts",
                    ip_address=ip_address,
                    blocked_until=ip_tracker.locked_until.isoformat(),
                )

        return self.check_account(username), self.check_ip(ip_address)

    def unlock_account(self, username: str, reason: str = "admin_unlock") -> bool:
        """Manually unlock an account.

        Args:
            username: Username to unlock
            reason: Reason for unlock

        Returns:
            True if account was unlocked
        """
        tracker = _get_user_tracker(username)
        if not tracker.locked:
            return False

        tracker.locked = False
        tracker.locked_at = None
        tracker.locked_until = None
        tracker.lock_reason = None
        tracker.failed_count = 0
        tracker.attempts.clear()

        logger.info(
            "Account manually unlocked",
            username=username,
            reason=reason,
        )
        return True

    def unblock_ip(self, ip_address: str) -> bool:
        """Manually unblock an IP address.

        Args:
            ip_address: IP to unblock

        Returns:
            True if IP was unblocked
        """
        # Remove from permanent block list
        _blocked_ips.discard(ip_address)

        tracker = _get_ip_tracker(ip_address)
        if not tracker.locked:
            return False

        tracker.locked = False
        tracker.locked_at = None
        tracker.locked_until = None
        tracker.failed_count = 0
        tracker.attempts.clear()

        logger.info("IP manually unblocked", ip_address=ip_address)
        return True

    def block_ip_permanently(self, ip_address: str, reason: str = "admin_action") -> None:
        """Permanently block an IP address.

        Args:
            ip_address: IP to block
            reason: Reason for block
        """
        _blocked_ips.add(ip_address)
        logger.warning(
            "IP permanently blocked",
            ip_address=ip_address,
            reason=reason,
        )

    def get_recent_attempts(
        self,
        username: str | None = None,
        ip_address: str | None = None,
        limit: int = 50,
    ) -> list[LoginAttempt]:
        """Get recent login attempts for audit.

        Args:
            username: Filter by username
            ip_address: Filter by IP
            limit: Maximum attempts to return

        Returns:
            List of recent attempts
        """
        attempts: list[LoginAttempt] = []

        if username:
            tracker = _get_user_tracker(username)
            attempts.extend(tracker.attempts)
        elif ip_address:
            tracker = _get_ip_tracker(ip_address)
            attempts.extend(tracker.attempts)
        else:
            # Get all attempts (expensive, use with caution)
            for tracker in _user_trackers.values():
                attempts.extend(tracker.attempts)

        # Sort by timestamp descending
        attempts.sort(key=lambda a: a.timestamp, reverse=True)
        return attempts[:limit]


# ========================================
# Singleton Instance
# ========================================

_protection_service: BruteForceProtectionService | None = None


def get_brute_force_protection_service(settings: Settings) -> BruteForceProtectionService:
    """Get brute force protection service instance."""
    global _protection_service
    if _protection_service is None:
        _protection_service = BruteForceProtectionService(settings)
    return _protection_service
