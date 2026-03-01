"""Consent mappers: domain entity <-> ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from shared.identity.models.consent import ConsentModel, ConsentScopeModel

if TYPE_CHECKING:
    from shared.identity.entities import Consent, ConsentScope


def consent_entity_to_model(entity: Consent) -> ConsentModel:
    """Convert Consent domain entity to ORM model."""
    model = ConsentModel(
        id=str(entity.id),
        user_id=str(entity.user_id) if entity.user_id else None,
        client_id=entity.client_id,
        remember=entity.remember,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        expires_at=entity.expires_at,
    )
    model.scopes = [consent_scope_entity_to_model(s) for s in entity.scopes]
    return model


def consent_model_to_entity(model: ConsentModel) -> Consent:
    """Convert ORM model to Consent domain entity."""
    from shared.identity.entities import Consent

    entity = Consent(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        client_id=model.client_id,
        remember=model.remember,
        created_at=model.created_at,
        updated_at=model.updated_at,
        expires_at=model.expires_at,
    )
    entity.scopes = [consent_scope_model_to_entity(s) for s in model.scopes]
    return entity


def consent_scope_entity_to_model(entity: ConsentScope) -> ConsentScopeModel:
    """Convert ConsentScope domain entity to ORM model."""
    return ConsentScopeModel(
        id=str(entity.id),
        consent_id=str(entity.consent_id) if entity.consent_id else None,
        scope=entity.scope,
        granted_at=entity.granted_at,
    )


def consent_scope_model_to_entity(model: ConsentScopeModel) -> ConsentScope:
    """Convert ORM model to ConsentScope domain entity."""
    from shared.identity.entities import ConsentScope

    return ConsentScope(
        id=uuid.UUID(model.id),
        consent_id=uuid.UUID(model.consent_id) if model.consent_id else None,
        scope=model.scope,
        granted_at=model.granted_at,
    )
