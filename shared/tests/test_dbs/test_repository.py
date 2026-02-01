"""Tests for shared.dbs.repository module.

This module tests the generic repository pattern implementation
including CRUD operations, filtering, and pagination.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from shared.dbs.repository import (
    AbstractRepository,
    Filter,
    FilterOperator,
    InMemoryRepository,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)


@dataclass
class SampleEntity:
    """Sample entity for repository tests."""
    id: str
    name: str
    age: int = 0
    active: bool = True


class TestFilterOperator:
    """Tests for FilterOperator enum."""

    def test_eq_operator(self) -> None:
        """Should have EQ operator."""
        assert FilterOperator.EQ.value == "eq"

    def test_ne_operator(self) -> None:
        """Should have NE operator."""
        assert FilterOperator.NE.value == "ne"

    def test_gt_operator(self) -> None:
        """Should have GT operator."""
        assert FilterOperator.GT.value == "gt"

    def test_gte_operator(self) -> None:
        """Should have GTE operator."""
        assert FilterOperator.GTE.value == "gte"

    def test_lt_operator(self) -> None:
        """Should have LT operator."""
        assert FilterOperator.LT.value == "lt"

    def test_lte_operator(self) -> None:
        """Should have LTE operator."""
        assert FilterOperator.LTE.value == "lte"

    def test_like_operator(self) -> None:
        """Should have LIKE operator."""
        assert FilterOperator.LIKE.value == "like"

    def test_in_operator(self) -> None:
        """Should have IN operator."""
        assert FilterOperator.IN.value == "in"


class TestFilter:
    """Tests for Filter dataclass."""

    def test_create_filter(self) -> None:
        """Should create a filter."""
        f = Filter(field="name", operator=FilterOperator.EQ, value="test")
        assert f.field == "name"
        assert f.operator == FilterOperator.EQ
        assert f.value == "test"

    def test_filter_with_default_operator(self) -> None:
        """Should default to EQ operator."""
        f = Filter(field="status", value="active")
        assert f.operator == FilterOperator.EQ


class TestOrderBy:
    """Tests for OrderBy dataclass."""

    def test_create_order_by(self) -> None:
        """Should create order by clause."""
        order = OrderBy(field="created_at", direction=OrderDirection.DESC)
        assert order.field == "created_at"
        assert order.direction == OrderDirection.DESC

    def test_default_direction_asc(self) -> None:
        """Should default to ASC direction."""
        order = OrderBy(field="name")
        assert order.direction == OrderDirection.ASC


class TestPageRequest:
    """Tests for PageRequest dataclass."""

    def test_create_page_request(self) -> None:
        """Should create page request."""
        page = PageRequest(page=1, size=20)
        assert page.page == 1
        assert page.size == 20

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        page = PageRequest()
        assert page.page == 1
        assert page.size == 10

    def test_offset_calculation(self) -> None:
        """Should calculate offset correctly."""
        page = PageRequest(page=3, size=10)
        assert page.offset == 20  # (3-1) * 10


class TestPageResponse:
    """Tests for PageResponse dataclass."""

    def test_create_page_response(self) -> None:
        """Should create page response."""
        items = [SampleEntity(id="1", name="Test")]
        response = PageResponse(
            items=items,
            total=100,
            page=1,
            size=10,
        )
        assert response.items == items
        assert response.total == 100

    def test_total_pages_calculation(self) -> None:
        """Should calculate total pages."""
        response = PageResponse(items=[], total=95, page=1, size=10)
        assert response.total_pages == 10  # ceil(95/10)

    def test_has_next_page(self) -> None:
        """Should indicate if next page exists."""
        response = PageResponse(items=[], total=100, page=1, size=10)
        assert response.has_next is True

        response2 = PageResponse(items=[], total=100, page=10, size=10)
        assert response2.has_next is False

    def test_has_previous_page(self) -> None:
        """Should indicate if previous page exists."""
        response = PageResponse(items=[], total=100, page=1, size=10)
        assert response.has_previous is False

        response2 = PageResponse(items=[], total=100, page=2, size=10)
        assert response2.has_previous is True


class TestAbstractRepository:
    """Tests for AbstractRepository interface."""

    def test_is_abstract(self) -> None:
        """Should be an abstract class."""
        with pytest.raises(TypeError):
            AbstractRepository()  # type: ignore[abstract]


class TestInMemoryRepository:
    """Tests for InMemoryRepository implementation."""

    @pytest.fixture
    def repo(self) -> InMemoryRepository[SampleEntity]:
        """Create a test repository."""
        return InMemoryRepository[SampleEntity](id_field="id")

    @pytest.mark.asyncio
    async def test_add_entity(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should add entity to repository."""
        entity = SampleEntity(id="1", name="Test")
        result = await repo.add(entity)
        assert result == entity

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should get entity by ID."""
        entity = SampleEntity(id="1", name="Test")
        await repo.add(entity)

        result = await repo.get("1")
        assert result == entity

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(
        self, repo: InMemoryRepository[SampleEntity]
    ) -> None:
        """Should return None for nonexistent entity."""
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should get all entities."""
        await repo.add(SampleEntity(id="1", name="First"))
        await repo.add(SampleEntity(id="2", name="Second"))

        result = await repo.get_all()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_update_entity(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should update existing entity."""
        entity = SampleEntity(id="1", name="Original")
        await repo.add(entity)

        updated = SampleEntity(id="1", name="Updated")
        result = await repo.update(updated)

        assert result.name == "Updated"
        fetched = await repo.get("1")
        assert fetched is not None
        assert fetched.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_entity(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should delete entity."""
        entity = SampleEntity(id="1", name="Test")
        await repo.add(entity)

        deleted = await repo.delete("1")
        assert deleted is True

        result = await repo.get("1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self, repo: InMemoryRepository[SampleEntity]
    ) -> None:
        """Should return False when deleting nonexistent."""
        deleted = await repo.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should check if entity exists."""
        entity = SampleEntity(id="1", name="Test")
        await repo.add(entity)

        assert await repo.exists("1") is True
        assert await repo.exists("2") is False

    @pytest.mark.asyncio
    async def test_count(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should count entities."""
        await repo.add(SampleEntity(id="1", name="First"))
        await repo.add(SampleEntity(id="2", name="Second"))

        assert await repo.count() == 2

    @pytest.mark.asyncio
    async def test_filter_eq(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should filter with EQ operator."""
        await repo.add(SampleEntity(id="1", name="Alice", age=30))
        await repo.add(SampleEntity(id="2", name="Bob", age=25))

        filters = [Filter(field="name", operator=FilterOperator.EQ, value="Alice")]
        result = await repo.find(filters=filters)

        assert len(result) == 1
        assert result[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_gt(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should filter with GT operator."""
        await repo.add(SampleEntity(id="1", name="Alice", age=30))
        await repo.add(SampleEntity(id="2", name="Bob", age=25))

        filters = [Filter(field="age", operator=FilterOperator.GT, value=26)]
        result = await repo.find(filters=filters)

        assert len(result) == 1
        assert result[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_in(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should filter with IN operator."""
        await repo.add(SampleEntity(id="1", name="Alice", age=30))
        await repo.add(SampleEntity(id="2", name="Bob", age=25))
        await repo.add(SampleEntity(id="3", name="Charlie", age=35))

        filters = [Filter(field="name", operator=FilterOperator.IN, value=["Alice", "Bob"])]
        result = await repo.find(filters=filters)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_order_by_asc(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should order results ascending."""
        await repo.add(SampleEntity(id="1", name="Zara", age=30))
        await repo.add(SampleEntity(id="2", name="Alice", age=25))

        order = [OrderBy(field="name", direction=OrderDirection.ASC)]
        result = await repo.find(order_by=order)

        assert result[0].name == "Alice"
        assert result[1].name == "Zara"

    @pytest.mark.asyncio
    async def test_order_by_desc(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should order results descending."""
        await repo.add(SampleEntity(id="1", name="Zara", age=30))
        await repo.add(SampleEntity(id="2", name="Alice", age=25))

        order = [OrderBy(field="name", direction=OrderDirection.DESC)]
        result = await repo.find(order_by=order)

        assert result[0].name == "Zara"
        assert result[1].name == "Alice"

    @pytest.mark.asyncio
    async def test_pagination(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should paginate results."""
        for i in range(25):
            await repo.add(SampleEntity(id=str(i), name=f"Entity{i}", age=i))

        page_request = PageRequest(page=2, size=10)
        response = await repo.find_paginated(page_request=page_request)

        assert len(response.items) == 10
        assert response.total == 25
        assert response.page == 2
        assert response.has_previous is True
        assert response.has_next is True

    @pytest.mark.asyncio
    async def test_find_one(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should find first matching entity."""
        await repo.add(SampleEntity(id="1", name="Alice", age=30))
        await repo.add(SampleEntity(id="2", name="Bob", age=30))

        filters = [Filter(field="age", operator=FilterOperator.EQ, value=30)]
        result = await repo.find_one(filters=filters)

        assert result is not None
        assert result.age == 30

    @pytest.mark.asyncio
    async def test_find_one_returns_none(
        self, repo: InMemoryRepository[SampleEntity]
    ) -> None:
        """Should return None when no match found."""
        await repo.add(SampleEntity(id="1", name="Alice", age=30))

        filters = [Filter(field="age", operator=FilterOperator.EQ, value=99)]
        result = await repo.find_one(filters=filters)

        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, repo: InMemoryRepository[SampleEntity]) -> None:
        """Should clear all entities."""
        await repo.add(SampleEntity(id="1", name="Test"))
        await repo.add(SampleEntity(id="2", name="Test2"))

        await repo.clear()

        assert await repo.count() == 0
