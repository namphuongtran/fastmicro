"""Tests for shared.extensions.dependency_injection module.

This module tests the dependency injection container and
related utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from unittest.mock import MagicMock

import pytest

from shared.extensions.dependency_injection import (
    Container,
    Depends,
    Scope,
    get_container,
    inject,
    register,
    resolve,
)


# Test interfaces and implementations
class IDatabase(Protocol):
    """Database interface."""

    def query(self, sql: str) -> list[dict]: ...


class ICache(Protocol):
    """Cache interface."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class MockDatabase:
    """Mock database implementation."""

    def query(self, sql: str) -> list[dict]:
        return [{"id": 1, "name": "test"}]


class MockCache:
    """Mock cache implementation."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


@dataclass
class AppConfig:
    """Application configuration."""

    debug: bool = False
    database_url: str = "sqlite:///:memory:"


class TestScope:
    """Tests for Scope enum."""

    def test_transient_scope(self) -> None:
        """Should have TRANSIENT scope."""
        assert Scope.TRANSIENT.value == "transient"

    def test_singleton_scope(self) -> None:
        """Should have SINGLETON scope."""
        assert Scope.SINGLETON.value == "singleton"

    def test_scoped_scope(self) -> None:
        """Should have SCOPED scope."""
        assert Scope.SCOPED.value == "scoped"


class TestContainer:
    """Tests for Container class."""

    @pytest.fixture
    def container(self) -> Container:
        """Create a fresh container."""
        return Container()

    def test_register_instance(self, container: Container) -> None:
        """Should register an instance."""
        config = AppConfig(debug=True)
        container.register_instance(AppConfig, config)

        resolved = container.resolve(AppConfig)
        assert resolved is config

    def test_register_factory(self, container: Container) -> None:
        """Should register a factory function."""
        container.register_factory(MockDatabase, lambda: MockDatabase())

        db = container.resolve(MockDatabase)
        assert isinstance(db, MockDatabase)

    def test_register_type(self, container: Container) -> None:
        """Should register a type for auto-instantiation."""
        container.register_type(MockCache)

        cache = container.resolve(MockCache)
        assert isinstance(cache, MockCache)

    def test_singleton_scope(self, container: Container) -> None:
        """Should return same instance for singleton scope."""
        container.register_type(MockCache, scope=Scope.SINGLETON)

        cache1 = container.resolve(MockCache)
        cache2 = container.resolve(MockCache)

        assert cache1 is cache2

    def test_transient_scope(self, container: Container) -> None:
        """Should return new instance for transient scope."""
        container.register_type(MockCache, scope=Scope.TRANSIENT)

        cache1 = container.resolve(MockCache)
        cache2 = container.resolve(MockCache)

        assert cache1 is not cache2

    def test_resolve_unregistered_raises(self, container: Container) -> None:
        """Should raise for unregistered type."""
        with pytest.raises(KeyError):
            container.resolve(MockDatabase)

    def test_register_interface_to_implementation(self, container: Container) -> None:
        """Should map interface to implementation."""
        container.register_type(MockDatabase, interface=IDatabase)

        db = container.resolve(IDatabase)
        assert isinstance(db, MockDatabase)

    def test_has_registered(self, container: Container) -> None:
        """Should check if type is registered."""
        assert container.has(MockCache) is False

        container.register_type(MockCache)

        assert container.has(MockCache) is True

    def test_clear_registrations(self, container: Container) -> None:
        """Should clear all registrations."""
        container.register_type(MockCache)
        container.register_type(MockDatabase)

        container.clear()

        assert container.has(MockCache) is False
        assert container.has(MockDatabase) is False


class TestInjectDecorator:
    """Tests for @inject decorator."""

    @pytest.fixture(autouse=True)
    def setup_container(self) -> None:
        """Set up global container."""
        container = get_container()
        container.clear()
        container.register_type(MockDatabase, interface=IDatabase)
        container.register_type(MockCache, interface=ICache)
        container.register_instance(AppConfig, AppConfig(debug=True))

    def test_injects_dependencies(self) -> None:
        """Should inject registered dependencies."""

        @inject
        def service_func(db: IDatabase = Depends(IDatabase)) -> list[dict]:
            return db.query("SELECT * FROM users")

        result = service_func()
        assert result == [{"id": 1, "name": "test"}]

    def test_injects_multiple_dependencies(self) -> None:
        """Should inject multiple dependencies."""

        @inject
        def multi_service(
            db: IDatabase = Depends(IDatabase),
            cache: ICache = Depends(ICache),
        ) -> str:
            cache.set("key", "value")
            return cache.get("key") or ""

        result = multi_service()
        assert result == "value"

    def test_allows_override(self) -> None:
        """Should allow manual override of dependencies."""

        @inject
        def overridable(db: IDatabase = Depends(IDatabase)) -> list[dict]:
            return db.query("SELECT 1")

        mock_db = MagicMock()
        mock_db.query.return_value = [{"custom": True}]

        result = overridable(db=mock_db)
        assert result == [{"custom": True}]

    @pytest.mark.asyncio
    async def test_async_inject(self) -> None:
        """Should work with async functions."""

        @inject
        async def async_service(
            config: AppConfig = Depends(AppConfig),
        ) -> bool:
            return config.debug

        result = await async_service()
        assert result is True


class TestDepends:
    """Tests for Depends marker."""

    def test_creates_dependency_marker(self) -> None:
        """Should create a dependency marker."""
        dep = Depends(IDatabase)
        assert dep.dependency is IDatabase

    def test_with_default_factory(self) -> None:
        """Should support default factory."""
        dep = Depends(IDatabase, default_factory=MockDatabase)
        assert dep.default_factory is MockDatabase


class TestGlobalContainer:
    """Tests for global container functions."""

    @pytest.fixture(autouse=True)
    def reset_container(self) -> None:
        """Reset global container before each test."""
        get_container().clear()

    def test_get_container_singleton(self) -> None:
        """Should return singleton container."""
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_register_function(self) -> None:
        """Should register via helper function."""
        register(MockDatabase, scope=Scope.SINGLETON)

        db = resolve(MockDatabase)
        assert isinstance(db, MockDatabase)

    def test_resolve_function(self) -> None:
        """Should resolve via helper function."""
        register(MockCache)

        cache = resolve(MockCache)
        assert isinstance(cache, MockCache)


class TestContainerScopes:
    """Tests for scoped containers."""

    def test_scoped_lifetime(self) -> None:
        """Should manage scoped lifetime."""
        container = Container()
        container.register_type(MockCache, scope=Scope.SCOPED)

        with container.create_scope() as scope:
            cache1 = scope.resolve(MockCache)
            cache2 = scope.resolve(MockCache)

            assert cache1 is cache2

        # New scope should give new instance
        with container.create_scope() as scope2:
            cache3 = scope2.resolve(MockCache)
            assert cache3 is not cache1
