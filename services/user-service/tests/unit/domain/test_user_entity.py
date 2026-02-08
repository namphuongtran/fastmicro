"""Unit tests for User aggregate root and domain events."""

from __future__ import annotations

import pytest

from user_service.domain.entities.user import (
    User,
    UserCreated,
    UserDeactivated,
    UserUpdated,
)
from user_service.domain.value_objects import UserEmail, UserPreference


# ---- User Factory ----

class TestUserCreate:
    """Tests for User.create factory method."""

    def test_create_sets_basic_attributes(self):
        user = User.create(
            id="u-1",
            email="test@example.com",
            display_name="Test User",
            first_name="Test",
            last_name="User",
            tenant_id="t-1",
        )
        assert user.id == "u-1"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.tenant_id == "t-1"
        assert user.is_active is True

    def test_create_sets_created_at(self):
        user = User.create(id="u-2", email="a@b.com", display_name="A")
        assert user.created_at is not None
        assert user.updated_at is None

    def test_create_raises_user_created_event(self):
        user = User.create(id="u-3", email="x@y.com", display_name="X")
        events = user.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserCreated)
        assert event.user_id == "u-3"
        assert event.email == "x@y.com"
        assert event.display_name == "X"
        assert event.aggregate_id == "u-3"
        assert event.aggregate_type == "User"

    def test_create_defaults_optional_fields(self):
        user = User.create(id="u-4", email="d@e.com", display_name="D")
        assert user.first_name == ""
        assert user.last_name == ""
        assert user.tenant_id is None
        assert user.preferences == {}


# ---- User Commands ----

class TestUserUpdateProfile:
    """Tests for User.update_profile command."""

    def test_update_display_name(self, sample_user: User):
        sample_user.update_profile(display_name="Alice Updated")
        assert sample_user.display_name == "Alice Updated"

    def test_update_multiple_fields(self, sample_user: User):
        sample_user.update_profile(first_name="Alicia", last_name="Smithson")
        assert sample_user.first_name == "Alicia"
        assert sample_user.last_name == "Smithson"

    def test_update_raises_user_updated_event(self, sample_user: User):
        # Clear the UserCreated event from factory
        sample_user.clear_events()
        sample_user.update_profile(display_name="New Name")
        events = sample_user.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserUpdated)
        assert event.user_id == sample_user.id
        assert "display_name" in event.changed_fields

    def test_update_records_changed_fields(self, sample_user: User):
        sample_user.clear_events()
        sample_user.update_profile(
            display_name="New", first_name="F", last_name="L"
        )
        event = sample_user.domain_events[0]
        assert isinstance(event, UserUpdated)
        assert set(event.changed_fields) == {"display_name", "first_name", "last_name"}

    def test_no_change_does_not_raise_event(self, sample_user: User):
        sample_user.clear_events()
        # Pass same values — no change
        sample_user.update_profile(
            display_name=sample_user.display_name,
            first_name=sample_user.first_name,
        )
        assert len(sample_user.domain_events) == 0

    def test_update_sets_updated_at(self, sample_user: User):
        assert sample_user.updated_at is None
        sample_user.update_profile(display_name="Updated")
        assert sample_user.updated_at is not None


class TestUserDeactivate:
    """Tests for User.deactivate command."""

    def test_deactivate_sets_inactive(self, sample_user: User):
        sample_user.deactivate(reason="requested")
        assert sample_user.is_active is False

    def test_deactivate_raises_event(self, sample_user: User):
        sample_user.clear_events()
        sample_user.deactivate(reason="compliance")
        events = sample_user.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserDeactivated)
        assert event.user_id == sample_user.id
        assert event.reason == "compliance"

    def test_deactivate_sets_updated_at(self, sample_user: User):
        sample_user.deactivate()
        assert sample_user.updated_at is not None


class TestUserSetPreference:
    """Tests for User.set_preference command."""

    def test_set_preference_adds_key(self, sample_user: User):
        sample_user.set_preference("theme", "dark")
        assert sample_user.preferences["theme"] == "dark"

    def test_set_preference_overwrites_existing(self, sample_user: User):
        sample_user.set_preference("lang", "en")
        sample_user.set_preference("lang", "fr")
        assert sample_user.preferences["lang"] == "fr"

    def test_set_preference_updates_timestamp(self, sample_user: User):
        sample_user.set_preference("k", "v")
        assert sample_user.updated_at is not None


class TestUserClearEvents:
    """Tests for event lifecycle on User aggregate."""

    def test_clear_events_returns_pending_events(self, sample_user: User):
        events = sample_user.clear_events()
        assert len(events) == 1
        assert isinstance(events[0], UserCreated)

    def test_clear_events_empties_queue(self, sample_user: User):
        sample_user.clear_events()
        assert len(sample_user.domain_events) == 0


# ---- Value Objects ----

class TestUserEmail:
    """Tests for UserEmail value object."""

    def test_valid_email(self):
        email = UserEmail(value="test@example.com")
        email.validate()  # Should not raise

    def test_invalid_email_no_at(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            UserEmail(value="invalid")

    def test_invalid_email_no_dot(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            UserEmail(value="test@localhost")


class TestUserPreference:
    """Tests for UserPreference value object."""

    def test_valid_preference(self):
        pref = UserPreference(key="theme", value="dark")
        pref.validate()  # Should not raise

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            UserPreference(key="  ", value="v")
