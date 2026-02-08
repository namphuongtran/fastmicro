"""Unit tests for UserApplicationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from shared.application.base_service import ConflictError, NotFoundError, ServiceContext

from user_service.application.dtos import CreateUserRequest, UpdateUserRequest
from user_service.application.services.user_service import UserApplicationService
from user_service.domain.entities.user import User


# ---- fixtures ----

@pytest.fixture
def mock_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.exists_by_email = AsyncMock(return_value=False)
    repo.add = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_by_tenant = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_dispatcher() -> AsyncMock:
    disp = AsyncMock()
    disp.dispatch = AsyncMock()
    return disp


@pytest.fixture
def service(mock_repository: AsyncMock, mock_dispatcher: AsyncMock) -> UserApplicationService:
    return UserApplicationService(
        repository=mock_repository,
        event_dispatcher=mock_dispatcher,
    )


@pytest.fixture
def create_dto() -> CreateUserRequest:
    return CreateUserRequest(
        email="alice@example.com",
        display_name="Alice",
        first_name="Alice",
        last_name="Smith",
        tenant_id="t-1",
    )


@pytest.fixture
def update_dto() -> UpdateUserRequest:
    return UpdateUserRequest(display_name="Alice Updated", first_name="Alicia")


@pytest.fixture
def existing_user() -> User:
    return User.create(
        id="user-existing",
        email="existing@example.com",
        display_name="Existing",
        tenant_id="t-1",
    )


# ---- create_user ----

class TestCreateUser:
    """Tests for UserApplicationService.create_user."""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        create_dto: CreateUserRequest,
    ):
        resp = await service.create_user(create_dto)

        assert resp.email == "alice@example.com"
        assert resp.display_name == "Alice"
        assert resp.is_active is True
        mock_repository.add.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_dispatches_event(
        self,
        service: UserApplicationService,
        mock_dispatcher: AsyncMock,
        create_dto: CreateUserRequest,
    ):
        await service.create_user(create_dto)
        mock_dispatcher.dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_conflict_on_duplicate_email(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        create_dto: CreateUserRequest,
    ):
        mock_repository.exists_by_email.return_value = True
        with pytest.raises(ConflictError, match="already registered"):
            await service.create_user(create_dto)

    @pytest.mark.asyncio
    async def test_create_user_tenant_from_context(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
    ):
        dto = CreateUserRequest(
            email="t@t.com", display_name="T", tenant_id=None
        )
        ctx = ServiceContext(tenant_id="ctx-tenant")
        resp = await service.create_user(dto, context=ctx)
        assert resp.tenant_id == "ctx-tenant"


# ---- get_user ----

class TestGetUser:
    """Tests for UserApplicationService.get_user."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
    ):
        mock_repository.get_by_id.return_value = existing_user
        resp = await service.get_user("user-existing")
        assert resp.id == "user-existing"

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
    ):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.get_user("nonexistent")


# ---- update_user ----

class TestUpdateUser:
    """Tests for UserApplicationService.update_user."""

    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
        update_dto: UpdateUserRequest,
    ):
        mock_repository.get_by_id.return_value = existing_user
        resp = await service.update_user("user-existing", update_dto)
        assert resp.display_name == "Alice Updated"
        assert resp.first_name == "Alicia"
        mock_repository.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        service: UserApplicationService,
        update_dto: UpdateUserRequest,
    ):
        with pytest.raises(NotFoundError):
            await service.update_user("missing", update_dto)

    @pytest.mark.asyncio
    async def test_update_user_no_changes(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
    ):
        mock_repository.get_by_id.return_value = existing_user
        empty_dto = UpdateUserRequest()
        await service.update_user("user-existing", empty_dto)
        mock_repository.update.assert_not_awaited()


# ---- deactivate_user ----

class TestDeactivateUser:
    """Tests for UserApplicationService.deactivate_user."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
    ):
        mock_repository.get_by_id.return_value = existing_user
        resp = await service.deactivate_user("user-existing")
        assert resp.is_active is False
        mock_repository.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(
        self,
        service: UserApplicationService,
    ):
        with pytest.raises(NotFoundError):
            await service.deactivate_user("missing")

    @pytest.mark.asyncio
    async def test_deactivate_with_context_reason(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        mock_dispatcher: AsyncMock,
        existing_user: User,
    ):
        mock_repository.get_by_id.return_value = existing_user
        ctx = ServiceContext(user_id="admin-5")
        await service.deactivate_user("user-existing", context=ctx)
        # The dispatched event should have reason containing admin-5
        dispatched_event = mock_dispatcher.dispatch.call_args[0][0]
        assert "admin-5" in dispatched_event.reason


# ---- delete_user ----

class TestDeleteUser:
    """Tests for UserApplicationService.delete_user."""

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
    ):
        mock_repository.get_by_id.return_value = existing_user
        await service.delete_user("user-existing")
        mock_repository.delete.assert_awaited_once_with("user-existing")

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        service: UserApplicationService,
    ):
        with pytest.raises(NotFoundError):
            await service.delete_user("missing")


# ---- list_users ----

class TestListUsers:
    """Tests for UserApplicationService.list_users."""

    @pytest.mark.asyncio
    async def test_list_users_returns_response(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
        existing_user: User,
    ):
        mock_repository.list_by_tenant.return_value = [existing_user]
        resp = await service.list_users(tenant_id="t-1")
        assert resp.total == 1
        assert len(resp.items) == 1
        assert resp.items[0].id == "user-existing"

    @pytest.mark.asyncio
    async def test_list_users_tenant_from_context(
        self,
        service: UserApplicationService,
        mock_repository: AsyncMock,
    ):
        ctx = ServiceContext(tenant_id="ctx-t")
        await service.list_users(context=ctx)
        mock_repository.list_by_tenant.assert_awaited_once()
        call_kwargs = mock_repository.list_by_tenant.call_args[1]
        assert call_kwargs["tenant_id"] == "ctx-t"

    @pytest.mark.asyncio
    async def test_list_users_empty(
        self,
        service: UserApplicationService,
    ):
        resp = await service.list_users()
        assert resp.total == 0
        assert resp.items == []
