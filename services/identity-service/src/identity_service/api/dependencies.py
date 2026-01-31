"""FastAPI dependencies for dependency injection."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from identity_service.application.services import OAuth2Service
from identity_service.configs import Settings, get_settings


# Placeholder for actual repository implementations
# These will be implemented in Phase 1 infrastructure layer

class InMemoryUserRepository:
    """In-memory user repository for development/testing."""

    async def get_by_id(self, user_id):
        return None

    async def get_by_email(self, email):
        return None

    async def get_by_username(self, username):
        return None

    async def get_by_external_id(self, external_id, provider):
        return None

    async def create(self, user):
        return user

    async def update(self, user):
        return user

    async def delete(self, user_id):
        return True

    async def exists_by_email(self, email):
        return False

    async def exists_by_username(self, username):
        return False

    async def find_by_role(self, role_name, skip=0, limit=100):
        return []

    async def count(self, include_inactive=False):
        return 0

    async def search(self, query, skip=0, limit=100, include_inactive=False):
        return []


class InMemoryClientRepository:
    """In-memory client repository for development/testing."""

    async def get_by_id(self, client_id):
        return None

    async def get_by_client_id(self, client_id):
        return None

    async def create(self, client):
        return client

    async def update(self, client):
        return client

    async def delete(self, client_id):
        return True

    async def exists_by_client_id(self, client_id):
        return False

    async def list_active(self, skip=0, limit=100):
        return []

    async def list_by_owner(self, owner_id, skip=0, limit=100):
        return []

    async def count(self, include_inactive=False):
        return 0

    async def search(self, query, skip=0, limit=100, include_inactive=False):
        return []


class InMemoryAuthCodeRepository:
    """In-memory auth code repository."""

    def __init__(self):
        self._codes = {}

    async def save(self, code):
        self._codes[code.code] = code

    async def get_by_code(self, code):
        return self._codes.get(code)

    async def delete(self, code):
        if code in self._codes:
            del self._codes[code]
            return True
        return False

    async def mark_as_used(self, code):
        if code in self._codes:
            self._codes[code].is_used = True
            return True
        return False


class InMemoryRefreshTokenRepository:
    """In-memory refresh token repository."""

    def __init__(self):
        self._tokens = {}

    async def save(self, token):
        self._tokens[token.token] = token
        return token

    async def get_by_token(self, token):
        return self._tokens.get(token)

    async def get_by_id(self, token_id):
        for t in self._tokens.values():
            if t.id == token_id:
                return t
        return None

    async def revoke(self, token, replaced_by=None):
        if token in self._tokens:
            self._tokens[token].revoke(replaced_by)
            return True
        return False

    async def revoke_all_for_user(self, user_id):
        count = 0
        for t in self._tokens.values():
            if t.user_id == user_id and not t.is_revoked:
                t.revoke()
                count += 1
        return count

    async def revoke_all_for_client(self, client_id):
        count = 0
        for t in self._tokens.values():
            if t.client_id == client_id and not t.is_revoked:
                t.revoke()
                count += 1
        return count

    async def revoke_all_for_user_and_client(self, user_id, client_id):
        count = 0
        for t in self._tokens.values():
            if t.user_id == user_id and t.client_id == client_id and not t.is_revoked:
                t.revoke()
                count += 1
        return count

    async def list_active_for_user(self, user_id, skip=0, limit=100):
        return [t for t in self._tokens.values() if t.user_id == user_id and t.is_valid()][skip:skip+limit]

    async def cleanup_expired(self):
        expired = [k for k, v in self._tokens.items() if v.is_expired()]
        for k in expired:
            del self._tokens[k]
        return len(expired)


class InMemoryTokenBlacklistRepository:
    """In-memory token blacklist repository."""

    def __init__(self):
        self._blacklist = {}

    async def add(self, entry):
        self._blacklist[entry.jti] = entry

    async def is_blacklisted(self, jti):
        return jti in self._blacklist

    async def remove(self, jti):
        if jti in self._blacklist:
            del self._blacklist[jti]
            return True
        return False


class InMemoryConsentRepository:
    """In-memory consent repository."""

    def __init__(self):
        self._consents = {}

    async def get_by_id(self, consent_id):
        return self._consents.get(str(consent_id))

    async def get_by_user_and_client(self, user_id, client_id):
        key = f"{user_id}:{client_id}"
        return self._consents.get(key)

    async def save(self, consent):
        key = f"{consent.user_id}:{consent.client_id}"
        self._consents[key] = consent
        return consent

    async def delete(self, consent_id):
        for k, v in list(self._consents.items()):
            if v.id == consent_id:
                del self._consents[k]
                return True
        return False

    async def delete_for_user(self, user_id):
        count = 0
        for k in list(self._consents.keys()):
            if k.startswith(str(user_id)):
                del self._consents[k]
                count += 1
        return count

    async def delete_for_client(self, client_id):
        count = 0
        for k in list(self._consents.keys()):
            if k.endswith(client_id):
                del self._consents[k]
                count += 1
        return count

    async def list_by_user(self, user_id, skip=0, limit=100):
        return [v for k, v in self._consents.items() if k.startswith(str(user_id))][skip:skip+limit]


class InMemorySessionRepository:
    """In-memory session repository."""

    def __init__(self):
        self._sessions = {}

    async def save(self, session):
        self._sessions[str(session.id)] = session

    async def get_by_id(self, session_id):
        return self._sessions.get(str(session_id))

    async def delete(self, session_id):
        key = str(session_id)
        if key in self._sessions:
            del self._sessions[key]
            return True
        return False

    async def delete_all_for_user(self, user_id):
        count = 0
        for k, v in list(self._sessions.items()):
            if v.user_id == user_id:
                del self._sessions[k]
                count += 1
        return count

    async def list_by_user(self, user_id):
        return [v for v in self._sessions.values() if v.user_id == user_id and v.is_valid()]

    async def update_activity(self, session_id):
        session = await self.get_by_id(session_id)
        if session:
            session.update_activity()
            return True
        return False

    async def extend(self, session_id, seconds):
        from datetime import timedelta
        session = await self.get_by_id(session_id)
        if session and session.expires_at:
            session.expires_at += timedelta(seconds=seconds)
            return True
        return False


# Singleton instances for in-memory repositories
_user_repo = InMemoryUserRepository()
_client_repo = InMemoryClientRepository()
_auth_code_repo = InMemoryAuthCodeRepository()
_refresh_token_repo = InMemoryRefreshTokenRepository()
_blacklist_repo = InMemoryTokenBlacklistRepository()
_consent_repo = InMemoryConsentRepository()
_session_repo = InMemorySessionRepository()


async def get_oauth2_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OAuth2Service:
    """Get OAuth2 service instance.

    Args:
        settings: Application settings

    Returns:
        OAuth2Service instance.
    """
    from identity_service.infrastructure.security import (
        get_jwt_service,
        get_password_service,
    )

    return OAuth2Service(
        settings=settings,
        jwt_service=get_jwt_service(settings),
        password_service=get_password_service(settings),
        user_repository=_user_repo,
        client_repository=_client_repo,
        auth_code_repository=_auth_code_repo,
        refresh_token_repository=_refresh_token_repo,
        token_blacklist_repository=_blacklist_repo,
        consent_repository=_consent_repo,
        session_repository=_session_repo,
    )
