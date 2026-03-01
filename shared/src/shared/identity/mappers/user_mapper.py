"""User aggregate mappers: domain entity <-> ORM model."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from shared.identity.models.user import (
    PasswordResetTokenModel,
    UserClaimModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
    UserRoleModel,
)

if TYPE_CHECKING:
    from identity_service.domain.entities import (
        User,
        UserClaim,
        UserCredential,
        UserProfile,
        UserRole,
    )
    from identity_service.domain.entities.password_reset import PasswordResetToken


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


def user_entity_to_model(entity: User) -> UserModel:
    """Convert User domain entity to ORM model."""
    model = UserModel(
        id=str(entity.id),
        email=entity.email,
        username=entity.username,
        is_active=entity.is_active,
        is_email_verified=entity.email_verified,
        external_id=entity.external_id,
        external_provider=entity.external_provider,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )

    if entity.credential:
        model.credential = credential_entity_to_model(entity.credential)

    if entity.profile:
        model.profile = profile_entity_to_model(entity.profile)

    model.claims = [claim_entity_to_model(c) for c in entity.claims]
    model.roles = [role_entity_to_model(r) for r in entity.roles]

    return model


def user_model_to_entity(model: UserModel) -> User:
    """Convert ORM model to User domain entity."""
    from identity_service.domain.entities import (
        User,
    )

    entity = User(
        id=uuid.UUID(model.id),
        email=model.email,
        username=model.username,
        is_active=model.is_active,
        email_verified=model.is_email_verified,
        external_id=model.external_id,
        external_provider=model.external_provider,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )

    if model.credential:
        entity.credential = credential_model_to_entity(model.credential)

    if model.profile:
        entity.profile = profile_model_to_entity(model.profile)

    entity.claims = [claim_model_to_entity(c) for c in model.claims]
    entity.roles = [role_model_to_entity(r) for r in model.roles]

    return entity


# ---------------------------------------------------------------------------
# UserCredential
# ---------------------------------------------------------------------------


def credential_entity_to_model(entity: UserCredential) -> UserCredentialModel:
    """Convert UserCredential domain entity to ORM model."""
    prev_hashes = (
        json.dumps(entity.previous_password_hashes) if entity.previous_password_hashes else None
    )
    recovery_codes = json.dumps(entity.mfa_recovery_codes) if entity.mfa_recovery_codes else None
    return UserCredentialModel(
        id=str(entity.id),
        user_id=str(entity.user_id) if entity.user_id else None,
        password_hash=entity.password_hash,
        password_changed_at=entity.password_changed_at,
        previous_password_hashes=prev_hashes,
        mfa_enabled=entity.mfa_enabled,
        mfa_secret=entity.mfa_secret,
        mfa_recovery_codes=recovery_codes,
        failed_login_attempts=entity.failed_login_attempts,
        locked_until=entity.locked_until,
        last_failed_login=entity.last_failed_login,
    )


def credential_model_to_entity(model: UserCredentialModel) -> UserCredential:
    """Convert ORM model to UserCredential domain entity."""
    from identity_service.domain.entities import UserCredential

    prev_hashes = (
        json.loads(model.previous_password_hashes) if model.previous_password_hashes else []
    )
    recovery_codes = json.loads(model.mfa_recovery_codes) if model.mfa_recovery_codes else []

    return UserCredential(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        password_hash=model.password_hash,
        password_changed_at=model.password_changed_at,
        previous_password_hashes=prev_hashes,
        mfa_enabled=model.mfa_enabled,
        mfa_secret=model.mfa_secret,
        mfa_recovery_codes=recovery_codes,
        failed_login_attempts=model.failed_login_attempts,
        locked_until=model.locked_until,
        last_failed_login=model.last_failed_login,
    )


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------


def profile_entity_to_model(entity: UserProfile) -> UserProfileModel:
    """Convert UserProfile domain entity to ORM model."""
    address_json = (
        json.dumps(entity.address) if isinstance(entity.address, dict) else entity.address
    )
    return UserProfileModel(
        id=str(entity.id),
        user_id=str(entity.user_id) if entity.user_id else None,
        given_name=entity.given_name,
        family_name=entity.family_name,
        middle_name=entity.middle_name,
        nickname=entity.nickname,
        preferred_username=entity.preferred_username,
        picture=entity.picture,
        website=entity.website,
        gender=entity.gender,
        birthdate=entity.birthdate,
        zoneinfo=entity.zoneinfo,
        locale=entity.locale,
        phone_number=entity.phone_number,
        phone_number_verified=entity.phone_number_verified,
        address=address_json,
        updated_at=entity.updated_at,
    )


def profile_model_to_entity(model: UserProfileModel) -> UserProfile:
    """Convert ORM model to UserProfile domain entity."""
    from identity_service.domain.entities import UserProfile

    address = json.loads(model.address) if model.address else None
    return UserProfile(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        given_name=model.given_name,
        family_name=model.family_name,
        middle_name=model.middle_name,
        nickname=model.nickname,
        preferred_username=model.preferred_username,
        picture=model.picture,
        website=model.website,
        gender=model.gender,
        birthdate=model.birthdate,
        zoneinfo=model.zoneinfo,
        locale=model.locale,
        phone_number=model.phone_number,
        phone_number_verified=model.phone_number_verified,
        address=address,
        updated_at=model.updated_at,
    )


# ---------------------------------------------------------------------------
# UserClaim
# ---------------------------------------------------------------------------


def claim_entity_to_model(entity: UserClaim) -> UserClaimModel:
    """Convert UserClaim domain entity to ORM model."""
    return UserClaimModel(
        id=str(entity.id),
        user_id=str(entity.user_id) if entity.user_id else None,
        claim_type=entity.claim_type,
        claim_value=entity.claim_value,
        issuer=entity.issuer,
    )


def claim_model_to_entity(model: UserClaimModel) -> UserClaim:
    """Convert ORM model to UserClaim domain entity."""
    from identity_service.domain.entities import UserClaim

    return UserClaim(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        claim_type=model.claim_type,
        claim_value=model.claim_value,
        issuer=model.issuer,
    )


# ---------------------------------------------------------------------------
# UserRole
# ---------------------------------------------------------------------------


def role_entity_to_model(entity: UserRole) -> UserRoleModel:
    """Convert UserRole domain entity to ORM model."""
    return UserRoleModel(
        id=str(entity.id),
        user_id=str(entity.user_id) if entity.user_id else None,
        role_name=entity.role_name,
        assigned_at=entity.assigned_at,
        expires_at=entity.expires_at,
        assigned_by=str(entity.assigned_by) if entity.assigned_by else None,
    )


def role_model_to_entity(model: UserRoleModel) -> UserRole:
    """Convert ORM model to UserRole domain entity."""
    from identity_service.domain.entities import UserRole

    return UserRole(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id) if model.user_id else None,
        role_name=model.role_name,
        assigned_at=model.assigned_at,
        expires_at=model.expires_at,
        assigned_by=uuid.UUID(model.assigned_by) if model.assigned_by else None,
    )


# ---------------------------------------------------------------------------
# PasswordResetToken
# ---------------------------------------------------------------------------


def password_reset_entity_to_model(
    entity: PasswordResetToken,
) -> PasswordResetTokenModel:
    """Convert PasswordResetToken domain entity to ORM model."""
    return PasswordResetTokenModel(
        id=str(entity.id),
        user_id=str(entity.user_id),
        token=entity.token,
        email=entity.email,
        expires_at=entity.expires_at,
        is_used=entity.is_used,
        used_at=entity.used_at,
        created_at=entity.created_at,
        ip_address=entity.ip_address,
    )


def password_reset_model_to_entity(
    model: PasswordResetTokenModel,
) -> PasswordResetToken:
    """Convert ORM model to PasswordResetToken domain entity."""
    from identity_service.domain.entities.password_reset import PasswordResetToken

    return PasswordResetToken(
        id=uuid.UUID(model.id),
        user_id=uuid.UUID(model.user_id),
        token=model.token,
        email=model.email,
        expires_at=model.expires_at,
        is_used=model.is_used,
        used_at=model.used_at,
        created_at=model.created_at,
        ip_address=model.ip_address,
    )
