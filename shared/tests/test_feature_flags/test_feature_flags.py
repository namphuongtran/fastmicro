"""Tests for shared.feature_flags — feature flag management."""

from __future__ import annotations

import pytest

from shared.feature_flags import (
    FeatureFlag,
    FeatureFlagProvider,
    FeatureFlagService,
    InMemoryFlagProvider,
    feature_enabled,
)


@pytest.mark.unit
class TestFeatureFlag:
    def test_defaults(self):
        f = FeatureFlag(name="my-flag")
        assert f.enabled is False
        assert f.rollout_percentage == 100.0
        assert f.allowed_users == set()
        assert f.denied_users == set()

    def test_custom_values(self):
        f = FeatureFlag(
            name="beta",
            enabled=True,
            rollout_percentage=50.0,
            allowed_users={"u1"},
            description="Beta feature",
        )
        assert f.enabled is True
        assert f.rollout_percentage == 50.0
        assert "u1" in f.allowed_users


@pytest.mark.unit
class TestInMemoryFlagProvider:
    async def test_set_and_get(self):
        p = InMemoryFlagProvider()
        p.set("flag-a", FeatureFlag(name="flag-a", enabled=True))
        flag = await p.get("flag-a")
        assert flag is not None
        assert flag.enabled is True

    async def test_get_missing(self):
        p = InMemoryFlagProvider()
        assert await p.get("nope") is None

    async def test_get_all(self):
        p = InMemoryFlagProvider()
        p.set("a", FeatureFlag(name="a"))
        p.set("b", FeatureFlag(name="b"))
        all_flags = await p.get_all()
        assert len(all_flags) == 2

    async def test_save_async(self):
        p = InMemoryFlagProvider()
        await p.save(FeatureFlag(name="x", enabled=True))
        assert (await p.get("x")) is not None

    async def test_delete(self):
        p = InMemoryFlagProvider()
        p.set("d", FeatureFlag(name="d"))
        await p.delete("d")
        assert await p.get("d") is None

    async def test_clear(self):
        p = InMemoryFlagProvider()
        p.set("a", FeatureFlag(name="a"))
        p.clear()
        assert await p.get("a") is None

    async def test_protocol_compliance(self):
        p = InMemoryFlagProvider()
        assert isinstance(p, FeatureFlagProvider)


@pytest.mark.unit
class TestFeatureFlagService:
    async def test_enabled_flag(self):
        provider = InMemoryFlagProvider()
        provider.set("f1", FeatureFlag(name="f1", enabled=True))
        svc = FeatureFlagService(provider=provider)
        assert await svc.is_enabled("f1") is True

    async def test_disabled_flag(self):
        provider = InMemoryFlagProvider()
        provider.set("f1", FeatureFlag(name="f1", enabled=False))
        svc = FeatureFlagService(provider=provider)
        assert await svc.is_enabled("f1") is False

    async def test_missing_flag_returns_default(self):
        provider = InMemoryFlagProvider()
        svc = FeatureFlagService(provider=provider)
        assert await svc.is_enabled("missing") is False
        assert await svc.is_enabled("missing", default=True) is True

    async def test_local_override(self):
        provider = InMemoryFlagProvider()
        provider.set("f1", FeatureFlag(name="f1", enabled=False))
        svc = FeatureFlagService(provider=provider, overrides={"f1": True})
        assert await svc.is_enabled("f1") is True

    async def test_deny_list(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "f1",
            FeatureFlag(name="f1", enabled=True, denied_users={"blocked-user"}),
        )
        svc = FeatureFlagService(provider=provider)
        assert await svc.is_enabled("f1", user_id="blocked-user") is False
        assert await svc.is_enabled("f1", user_id="normal-user") is True

    async def test_allow_list(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "f1",
            FeatureFlag(
                name="f1",
                enabled=True,
                rollout_percentage=0.0,
                allowed_users={"vip"},
            ),
        )
        svc = FeatureFlagService(provider=provider)
        # VIP is in allow list — should be enabled despite 0% rollout
        assert await svc.is_enabled("f1", user_id="vip") is True
        # Non-VIP with 0% rollout — should be disabled
        assert await svc.is_enabled("f1", user_id="regular") is False

    async def test_percentage_rollout_deterministic(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "f1",
            FeatureFlag(name="f1", enabled=True, rollout_percentage=50.0),
        )
        svc = FeatureFlagService(provider=provider)

        # Same user should always get the same result
        r1 = await svc.is_enabled("f1", user_id="user-42")
        r2 = await svc.is_enabled("f1", user_id="user-42")
        assert r1 == r2

    async def test_percentage_rollout_without_user_id(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "f1",
            FeatureFlag(name="f1", enabled=True, rollout_percentage=50.0),
        )
        svc = FeatureFlagService(provider=provider)
        # No user_id → returns default
        assert await svc.is_enabled("f1") is False

    async def test_full_rollout_no_user_id_needed(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "f1",
            FeatureFlag(name="f1", enabled=True, rollout_percentage=100.0),
        )
        svc = FeatureFlagService(provider=provider)
        assert await svc.is_enabled("f1") is True

    async def test_get_set_delete_flag(self):
        provider = InMemoryFlagProvider()
        svc = FeatureFlagService(provider=provider)

        await svc.set_flag(FeatureFlag(name="new", enabled=True))
        flag = await svc.get_flag("new")
        assert flag is not None

        await svc.delete_flag("new")
        assert await svc.get_flag("new") is None

    async def test_get_all_flags(self):
        provider = InMemoryFlagProvider()
        provider.set("a", FeatureFlag(name="a"))
        provider.set("b", FeatureFlag(name="b"))
        svc = FeatureFlagService(provider=provider)
        all_flags = await svc.get_all_flags()
        assert len(all_flags) == 2


@pytest.mark.unit
class TestFeatureEnabledHelper:
    async def test_feature_enabled_convenience(self):
        provider = InMemoryFlagProvider()
        provider.set("fast", FeatureFlag(name="fast", enabled=True))
        assert await feature_enabled(provider, "fast") is True
        assert await feature_enabled(provider, "unknown") is False

    async def test_feature_enabled_with_user(self):
        provider = InMemoryFlagProvider()
        provider.set(
            "beta",
            FeatureFlag(name="beta", enabled=True, rollout_percentage=50.0),
        )
        # Just ensure it doesn't throw — exact result is hash-dependent
        result = await feature_enabled(provider, "beta", user_id="user-1")
        assert isinstance(result, bool)
