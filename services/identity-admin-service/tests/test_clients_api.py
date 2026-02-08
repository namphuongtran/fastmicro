"""Tests for OAuth clients admin API."""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_clients_empty(client: AsyncClient) -> None:
    """Test listing clients when none exist."""
    response = await client.get("/api/admin/clients")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.anyio
async def test_create_client(
    client: AsyncClient,
    sample_client_data: dict[str, Any],
) -> None:
    """Test creating a new OAuth client."""
    response = await client.post(
        "/api/admin/clients",
        json=sample_client_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_name"] == sample_client_data["client_name"]
    assert data["client_type"] == sample_client_data["client_type"]
    assert "client_id" in data
    assert "id" in data
    # Note: client_secret is returned only when generating a new secret


@pytest.mark.anyio
async def test_create_client_validation_error(client: AsyncClient) -> None:
    """Test client creation with invalid data."""
    response = await client.post(
        "/api/admin/clients",
        json={
            "client_name": "",  # Empty name should fail
            "client_type": "invalid_type",
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_client_not_found(client: AsyncClient) -> None:
    """Test getting a non-existent client."""
    response = await client.get(f"/api/admin/clients/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_client_lifecycle(
    client: AsyncClient,
    sample_client_data: dict[str, Any],
) -> None:
    """Test full client lifecycle: create, read, update, delete."""
    # Create
    create_response = await client.post(
        "/api/admin/clients",
        json=sample_client_data,
    )
    assert create_response.status_code == 201
    created_client = create_response.json()
    client_id = created_client["id"]

    # Read
    get_response = await client.get(f"/api/admin/clients/{client_id}")
    assert get_response.status_code == 200
    fetched_client = get_response.json()
    assert fetched_client["client_name"] == sample_client_data["client_name"]

    # Update
    update_response = await client.patch(
        f"/api/admin/clients/{client_id}",
        json={"client_name": "Updated Application"},
    )
    assert update_response.status_code == 200
    updated_client = update_response.json()
    assert updated_client["client_name"] == "Updated Application"

    # Delete
    delete_response = await client.delete(f"/api/admin/clients/{client_id}")
    assert delete_response.status_code == 204


@pytest.mark.anyio
async def test_regenerate_client_secret(
    client: AsyncClient,
    sample_client_data: dict[str, Any],
) -> None:
    """Test regenerating client secret."""
    # Create client
    create_response = await client.post(
        "/api/admin/clients",
        json=sample_client_data,
    )
    assert create_response.status_code == 201
    created_client = create_response.json()
    client_id = created_client["id"]

    # Regenerate secret
    regen_response = await client.post(
        f"/api/admin/clients/{client_id}/secrets",
        json={"description": "Test secret"},
    )
    assert regen_response.status_code == 201
    new_secret_data = regen_response.json()

    # Secret should be returned
    assert "secret" in new_secret_data

    # Cleanup
    await client.delete(f"/api/admin/clients/{client_id}")


@pytest.mark.anyio
async def test_client_pagination(
    client: AsyncClient,
    sample_client_data: dict[str, Any],
) -> None:
    """Test client listing pagination."""
    # Create multiple clients
    client_ids = []
    for i in range(5):
        data = {**sample_client_data, "client_name": f"Test Client {i}"}
        response = await client.post("/api/admin/clients", json=data)
        assert response.status_code == 201
        client_ids.append(response.json()["id"])

    # Test pagination
    response = await client.get("/api/admin/clients?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Cleanup
    for cid in client_ids:
        await client.delete(f"/api/admin/clients/{cid}")


@pytest.mark.anyio
async def test_activate_deactivate_client(
    client: AsyncClient,
    sample_client_data: dict[str, Any],
) -> None:
    """Test activating and deactivating a client."""
    # Create client
    create_response = await client.post(
        "/api/admin/clients",
        json=sample_client_data,
    )
    assert create_response.status_code == 201
    client_id = create_response.json()["id"]

    # Deactivate
    deactivate_response = await client.post(
        f"/api/admin/clients/{client_id}/deactivate",
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # Activate
    activate_response = await client.post(
        f"/api/admin/clients/{client_id}/activate",
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    # Cleanup
    await client.delete(f"/api/admin/clients/{client_id}")
