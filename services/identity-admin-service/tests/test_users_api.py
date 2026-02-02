"""Tests for users admin API."""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_users_empty(client: AsyncClient) -> None:
    """Test listing users when none exist."""
    response = await client.get("/api/admin/users")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.anyio
async def test_create_user(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test creating a new user."""
    response = await client.post(
        "/api/admin/users",
        json=sample_user_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == sample_user_data["username"]
    assert data["email"] == sample_user_data["email"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned


@pytest.mark.anyio
async def test_create_user_validation_error(client: AsyncClient) -> None:
    """Test user creation with invalid data."""
    response = await client.post(
        "/api/admin/users",
        json={
            "username": "",  # Empty username should fail
            "email": "invalid-email",  # Invalid email
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_user_not_found(client: AsyncClient) -> None:
    """Test getting a non-existent user."""
    response = await client.get(f"/api/admin/users/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_lifecycle(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test full user lifecycle: create, read, update, delete."""
    # Create
    create_response = await client.post(
        "/api/admin/users",
        json=sample_user_data,
    )
    assert create_response.status_code == 201
    created_user = create_response.json()
    user_id = created_user["id"]

    # Read
    get_response = await client.get(f"/api/admin/users/{user_id}")
    assert get_response.status_code == 200
    fetched_user = get_response.json()
    assert fetched_user["username"] == sample_user_data["username"]

    # Update
    update_response = await client.patch(
        f"/api/admin/users/{user_id}",
        json={"email": "updated@example.com"},
    )
    assert update_response.status_code == 200
    updated_user = update_response.json()
    assert updated_user["email"] == "updated@example.com"

    # Delete
    delete_response = await client.delete(f"/api/admin/users/{user_id}")
    assert delete_response.status_code == 204


@pytest.mark.anyio
async def test_activate_deactivate_user(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test activating and deactivating a user."""
    # Create user
    create_response = await client.post(
        "/api/admin/users",
        json=sample_user_data,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Deactivate
    deactivate_response = await client.post(
        f"/api/admin/users/{user_id}/deactivate",
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # Activate
    activate_response = await client.post(
        f"/api/admin/users/{user_id}/activate",
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    # Cleanup
    await client.delete(f"/api/admin/users/{user_id}")


@pytest.mark.anyio
async def test_lock_unlock_user(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test locking and unlocking a user."""
    # Create user
    create_response = await client.post(
        "/api/admin/users",
        json=sample_user_data,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Lock
    lock_response = await client.post(
        f"/api/admin/users/{user_id}/lock",
    )
    assert lock_response.status_code == 200
    assert lock_response.json()["is_locked"] is True

    # Unlock
    unlock_response = await client.post(
        f"/api/admin/users/{user_id}/unlock",
    )
    assert unlock_response.status_code == 200
    assert unlock_response.json()["is_locked"] is False

    # Cleanup
    await client.delete(f"/api/admin/users/{user_id}")


@pytest.mark.anyio
async def test_reset_password(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test resetting user password."""
    # Create user
    create_response = await client.post(
        "/api/admin/users",
        json=sample_user_data,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Reset password
    reset_response = await client.post(
        f"/api/admin/users/{user_id}/reset-password",
        json={"new_password": "NewSecureP@ssw0rd!"},
    )
    assert reset_response.status_code == 204

    # Cleanup
    await client.delete(f"/api/admin/users/{user_id}")


@pytest.mark.anyio
async def test_user_pagination(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test user listing pagination."""
    # Create multiple users
    user_ids = []
    for i in range(5):
        data = {
            **sample_user_data,
            "username": f"testuser{i}",
            "email": f"test{i}@example.com",
        }
        response = await client.post("/api/admin/users", json=data)
        assert response.status_code == 201
        user_ids.append(response.json()["id"])

    # Test pagination
    response = await client.get("/api/admin/users?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Cleanup
    for uid in user_ids:
        await client.delete(f"/api/admin/users/{uid}")


@pytest.mark.anyio
async def test_manage_user_roles(
    client: AsyncClient,
    sample_user_data: dict[str, Any],
) -> None:
    """Test managing user roles."""
    # Create user without roles
    data = {**sample_user_data, "roles": []}
    create_response = await client.post("/api/admin/users", json=data)
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Add role
    add_role_response = await client.post(
        f"/api/admin/users/{user_id}/roles",
        json={"role_name": "admin"},
    )
    assert add_role_response.status_code == 200

    # Verify role added
    get_response = await client.get(f"/api/admin/users/{user_id}")
    assert get_response.status_code == 200
    user = get_response.json()
    assert "admin" in user.get("roles", [])

    # Remove role
    remove_role_response = await client.delete(
        f"/api/admin/users/{user_id}/roles/admin",
    )
    assert remove_role_response.status_code == 204

    # Cleanup
    await client.delete(f"/api/admin/users/{user_id}")
