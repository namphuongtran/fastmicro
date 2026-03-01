"""Token mappers: domain entity <-> ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from shared.identity.models.token import RefreshTokenModel

if TYPE_CHECKING:
    from shared.identity.entities import RefreshToken


def refresh_token_entity_to_model(entity: RefreshToken) -> RefreshTokenModel:
    """Convert RefreshToken domain entity to ORM model."""
    return RefreshTokenModel(
        id=str(entity.id),
        token=entity.token,
        client_id=entity.client_id,
        user_id=str(entity.user_id) if entity.user_id else None,
        scope=entity.scope,
        issued_at=entity.issued_at,
        expires_at=entity.expires_at,
        is_revoked=entity.is_revoked,
        revoked_at=entity.revoked_at,
        replaced_by=entity.replaced_by,
        parent_token=entity.parent_token,
    )


def refresh_token_model_to_entity(model: RefreshTokenModel) -> RefreshToken:
    """Convert ORM model to RefreshToken domain entity."""
    from shared.identity.entities import RefreshToken

    return RefreshToken(
        id=uuid.UUID(model.id),
        token=model.token,
        client_id=model.client_id,
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        scope=model.scope,
        issued_at=model.issued_at,
        expires_at=model.expires_at,
        is_revoked=model.is_revoked,
        revoked_at=model.revoked_at,
        replaced_by=model.replaced_by,
        parent_token=model.parent_token,
    )
