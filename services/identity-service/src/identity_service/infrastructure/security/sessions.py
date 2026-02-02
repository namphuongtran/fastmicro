"""Session Management Service.

Features:
- Track active user sessions
- List all sessions for a user
- Revoke individual sessions
- Revoke all sessions (force logout everywhere)
- Session metadata (device, location, etc.)
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from shared.observability import get_structlog_logger

if TYPE_CHECKING:
    from identity_service.configs.settings import Settings

logger = get_structlog_logger(__name__)


# ========================================
# Types and Data Classes
# ========================================


class SessionStatus(str, Enum):
    """Session status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class SessionInfo:
    """Information about a user session."""

    session_id: str
    user_id: str
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE

    # Device/client info
    ip_address: str | None = None
    user_agent: str | None = None
    device_type: str | None = None
    device_name: str | None = None
    browser: str | None = None
    os: str | None = None
    location: str | None = None

    # OAuth info
    client_id: str | None = None
    scope: str | None = None

    # Metadata
    is_current: bool = False  # Is this the requesting session?
    revoked_at: datetime | None = None
    revoke_reason: str | None = None


@dataclass
class SessionCreateResult:
    """Result of session creation."""

    session_id: str
    session_token: str  # For cookie/header
    expires_at: datetime


# ========================================
# In-Memory Storage (Replace with Redis in production)
# ========================================

# session_id -> SessionInfo
_sessions: dict[str, SessionInfo] = {}

# session_token_hash -> session_id
_token_to_session: dict[str, str] = {}

# user_id -> set of session_ids
_user_sessions: dict[str, set[str]] = {}


def _hash_token(token: str) -> str:
    """Hash session token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _parse_user_agent(user_agent: str | None) -> dict:
    """Parse user agent string for device info.

    Returns dict with device_type, browser, os.
    """
    if not user_agent:
        return {}

    result = {
        "device_type": "unknown",
        "browser": "unknown",
        "os": "unknown",
    }

    ua_lower = user_agent.lower()

    # Detect device type
    if "mobile" in ua_lower or "android" in ua_lower:
        result["device_type"] = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        result["device_type"] = "tablet"
    else:
        result["device_type"] = "desktop"

    # Detect browser
    if "chrome" in ua_lower and "edg" not in ua_lower:
        result["browser"] = "Chrome"
    elif "firefox" in ua_lower:
        result["browser"] = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        result["browser"] = "Safari"
    elif "edg" in ua_lower:
        result["browser"] = "Edge"
    elif "msie" in ua_lower or "trident" in ua_lower:
        result["browser"] = "Internet Explorer"

    # Detect OS
    if "windows" in ua_lower:
        result["os"] = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        result["os"] = "macOS"
    elif "linux" in ua_lower:
        result["os"] = "Linux"
    elif "android" in ua_lower:
        result["os"] = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        result["os"] = "iOS"

    return result


# ========================================
# Session Management Service
# ========================================


class SessionManagementService:
    """Service for managing user sessions."""

    def __init__(self, settings: Settings) -> None:
        """Initialize session service.

        Args:
            settings: Application settings
        """
        self._settings = settings

        # Default configuration
        self.session_lifetime_hours = getattr(settings, "session_lifetime_hours", 24)
        self.max_sessions_per_user = getattr(settings, "max_sessions_per_user", 10)
        self.session_idle_timeout_minutes = getattr(settings, "session_idle_timeout_minutes", 60)

    def create_session(
        self,
        user_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        client_id: str | None = None,
        scope: str | None = None,
    ) -> SessionCreateResult:
        """Create a new session for a user.

        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent string
            client_id: OAuth client ID
            scope: Granted scope

        Returns:
            Session creation result with token
        """
        now = datetime.now(UTC)

        # Generate session ID and token
        session_id = str(uuid4())
        session_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(session_token)

        # Calculate expiry
        expires_at = now + timedelta(hours=self.session_lifetime_hours)

        # Parse user agent
        ua_info = _parse_user_agent(user_agent)

        # Create session
        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=ua_info.get("device_type"),
            browser=ua_info.get("browser"),
            os=ua_info.get("os"),
            client_id=client_id,
            scope=scope,
        )

        # Store session
        _sessions[session_id] = session
        _token_to_session[token_hash] = session_id

        # Track by user
        if user_id not in _user_sessions:
            _user_sessions[user_id] = set()
        _user_sessions[user_id].add(session_id)

        # Enforce max sessions limit
        self._enforce_session_limit(user_id)

        logger.info(
            "Session created",
            session_id=session_id,
            user_id=user_id,
            device_type=ua_info.get("device_type"),
        )

        return SessionCreateResult(
            session_id=session_id,
            session_token=session_token,
            expires_at=expires_at,
        )

    def validate_session(
        self,
        session_token: str,
        update_activity: bool = True,
    ) -> SessionInfo | None:
        """Validate a session token.

        Args:
            session_token: Session token to validate
            update_activity: Whether to update last activity time

        Returns:
            Session info if valid, None otherwise
        """
        token_hash = _hash_token(session_token)
        session_id = _token_to_session.get(token_hash)

        if not session_id:
            return None

        session = _sessions.get(session_id)
        if not session:
            return None

        now = datetime.now(UTC)

        # Check if expired
        if session.expires_at < now:
            session.status = SessionStatus.EXPIRED
            return None

        # Check if revoked
        if session.status == SessionStatus.REVOKED:
            return None

        # Check idle timeout
        idle_cutoff = now - timedelta(minutes=self.session_idle_timeout_minutes)
        if session.last_activity_at < idle_cutoff:
            session.status = SessionStatus.EXPIRED
            logger.info("Session expired due to inactivity", session_id=session_id)
            return None

        # Update activity
        if update_activity:
            session.last_activity_at = now

        return session

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session info or None
        """
        return _sessions.get(session_id)

    def get_user_sessions(
        self,
        user_id: str,
        include_expired: bool = False,
        current_session_id: str | None = None,
    ) -> list[SessionInfo]:
        """Get all sessions for a user.

        Args:
            user_id: User identifier
            include_expired: Include expired/revoked sessions
            current_session_id: Mark this session as current

        Returns:
            List of sessions
        """
        session_ids = _user_sessions.get(user_id, set())
        sessions: list[SessionInfo] = []
        now = datetime.now(UTC)

        for sid in session_ids:
            session = _sessions.get(sid)
            if not session:
                continue

            # Check expiry
            if session.expires_at < now:
                session.status = SessionStatus.EXPIRED

            if not include_expired and session.status != SessionStatus.ACTIVE:
                continue

            # Mark current session
            if current_session_id and session.session_id == current_session_id:
                session.is_current = True
            else:
                session.is_current = False

            sessions.append(session)

        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.last_activity_at, reverse=True)
        return sessions

    def revoke_session(
        self,
        session_id: str,
        reason: str = "user_logout",
    ) -> bool:
        """Revoke a specific session.

        Args:
            session_id: Session to revoke
            reason: Reason for revocation

        Returns:
            True if session was revoked
        """
        session = _sessions.get(session_id)
        if not session:
            return False

        session.status = SessionStatus.REVOKED
        session.revoked_at = datetime.now(UTC)
        session.revoke_reason = reason

        logger.info(
            "Session revoked",
            session_id=session_id,
            user_id=session.user_id,
            reason=reason,
        )

        return True

    def revoke_all_sessions(
        self,
        user_id: str,
        except_session_id: str | None = None,
        reason: str = "logout_all",
    ) -> int:
        """Revoke all sessions for a user.

        Args:
            user_id: User identifier
            except_session_id: Keep this session active (current session)
            reason: Reason for revocation

        Returns:
            Number of sessions revoked
        """
        session_ids = _user_sessions.get(user_id, set())
        revoked_count = 0

        for sid in session_ids:
            if except_session_id and sid == except_session_id:
                continue

            if self.revoke_session(sid, reason):
                revoked_count += 1

        logger.info(
            "All user sessions revoked",
            user_id=user_id,
            revoked_count=revoked_count,
            kept_session=except_session_id,
        )

        return revoked_count

    def revoke_sessions_by_client(
        self,
        user_id: str,
        client_id: str,
        reason: str = "client_revoked",
    ) -> int:
        """Revoke all sessions for a user from a specific client.

        Args:
            user_id: User identifier
            client_id: OAuth client ID
            reason: Reason for revocation

        Returns:
            Number of sessions revoked
        """
        session_ids = _user_sessions.get(user_id, set())
        revoked_count = 0

        for sid in session_ids:
            session = _sessions.get(sid)
            if session and session.client_id == client_id:
                if self.revoke_session(sid, reason):
                    revoked_count += 1

        return revoked_count

    def _enforce_session_limit(self, user_id: str) -> None:
        """Enforce maximum sessions per user.

        Revokes oldest sessions if limit exceeded.
        """
        sessions = self.get_user_sessions(user_id)

        if len(sessions) <= self.max_sessions_per_user:
            return

        # Sort by last activity (oldest first)
        sessions.sort(key=lambda s: s.last_activity_at)

        # Revoke oldest sessions
        to_revoke = len(sessions) - self.max_sessions_per_user
        for i in range(to_revoke):
            self.revoke_session(sessions[i].session_id, "session_limit_exceeded")

        logger.info(
            "Enforced session limit",
            user_id=user_id,
            revoked=to_revoke,
        )

    def cleanup_expired_sessions(self) -> int:
        """Remove expired and revoked sessions from storage.

        Should be run periodically.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(UTC)
        # Keep revoked sessions for 24 hours for audit
        cleanup_cutoff = now - timedelta(hours=24)

        to_remove: list[str] = []

        for session_id, session in _sessions.items():
            should_remove = False

            if session.status == SessionStatus.EXPIRED and session.expires_at < cleanup_cutoff:
                should_remove = True
            elif session.status == SessionStatus.REVOKED and session.revoked_at:
                if session.revoked_at < cleanup_cutoff:
                    should_remove = True

            if should_remove:
                to_remove.append(session_id)

        # Remove sessions
        for session_id in to_remove:
            session = _sessions.pop(session_id, None)
            if session:
                # Remove from user's session list
                user_sessions = _user_sessions.get(session.user_id)
                if user_sessions:
                    user_sessions.discard(session_id)

                # Remove token mapping
                for token_hash, sid in list(_token_to_session.items()):
                    if sid == session_id:
                        _token_to_session.pop(token_hash, None)
                        break

        if to_remove:
            logger.info("Cleaned up expired sessions", count=len(to_remove))

        return len(to_remove)


# ========================================
# Singleton Instance
# ========================================

_session_service: SessionManagementService | None = None


def get_session_management_service(settings: Settings) -> SessionManagementService:
    """Get session management service instance."""
    global _session_service
    if _session_service is None:
        _session_service = SessionManagementService(settings)
    return _session_service
