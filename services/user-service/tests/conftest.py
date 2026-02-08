"""Shared fixtures for user-service tests."""

from __future__ import annotations

from typing import Any

import pytest

from user_service.domain.entities.user import User


@pytest.fixture
def sample_user() -> User:
    """Create a sample User aggregate for testing."""
    return User.create(
        id="user-001",
        email="alice@example.com",
        display_name="Alice Smith",
        first_name="Alice",
        last_name="Smith",
        tenant_id="tenant-1",
    )


@pytest.fixture
def user_data() -> dict[str, Any]:
    """Raw data for creating a user."""
    return {
        "id": "user-002",
        "email": "bob@example.com",
        "display_name": "Bob Jones",
        "first_name": "Bob",
        "last_name": "Jones",
        "tenant_id": "tenant-1",
    }
