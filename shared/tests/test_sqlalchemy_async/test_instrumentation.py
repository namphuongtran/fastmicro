"""Tests for SQLAlchemy OpenTelemetry instrumentation utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shared.sqlalchemy_async.instrumentation import (
    SQLAlchemyInstrumentationConfig,
    configure_sqlalchemy_instrumentation,
    instrument_engine,
    reset_sqlalchemy_instrumentation,
    uninstrument_engine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_instrumentation():
    """Reset global instrumentation state between tests."""
    reset_sqlalchemy_instrumentation()
    yield
    reset_sqlalchemy_instrumentation()


_INSTRUMENTOR_CLS = "opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor"


@pytest.fixture()
def mock_instrumentor():
    """Patch the SQLAlchemyInstrumentor."""
    with patch(_INSTRUMENTOR_CLS, autospec=False) as cls:
        instance = MagicMock()
        cls.return_value = instance
        yield instance


# ---------------------------------------------------------------------------
# SQLAlchemyInstrumentationConfig
# ---------------------------------------------------------------------------


class TestConfig:
    def test_defaults(self):
        cfg = SQLAlchemyInstrumentationConfig()
        assert cfg.service_name == "unknown-service"
        assert cfg.enable_commenter is False
        assert cfg.commenter_options == {}
        assert cfg.extra_attributes == {}

    def test_custom_values(self):
        cfg = SQLAlchemyInstrumentationConfig(
            service_name="audit-service",
            enable_commenter=True,
            commenter_options={"route": True},
            extra_attributes={"tier": "prod"},
        )
        assert cfg.service_name == "audit-service"
        assert cfg.enable_commenter is True
        assert cfg.commenter_options == {"route": True}

    def test_frozen(self):
        cfg = SQLAlchemyInstrumentationConfig()
        with pytest.raises(AttributeError):
            cfg.service_name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# instrument_engine
# ---------------------------------------------------------------------------


class TestInstrumentEngine:
    def test_calls_instrumentor(self, mock_instrumentor):
        engine = MagicMock(spec=[])  # no sync_engine attr
        instrument_engine(engine, service_name="test-svc")
        mock_instrumentor.instrument.assert_called_once()
        call_kwargs = mock_instrumentor.instrument.call_args[1]
        assert call_kwargs["engine"] is engine

    def test_extracts_sync_engine_from_async(self, mock_instrumentor):
        async_engine = MagicMock()
        sync_engine = MagicMock()
        async_engine.sync_engine = sync_engine

        instrument_engine(async_engine)
        call_kwargs = mock_instrumentor.instrument.call_args[1]
        assert call_kwargs["engine"] is sync_engine

    def test_enable_commenter(self, mock_instrumentor):
        engine = MagicMock(spec=[])
        instrument_engine(
            engine,
            enable_commenter=True,
            commenter_options={"route": True},
        )
        call_kwargs = mock_instrumentor.instrument.call_args[1]
        assert call_kwargs["enable_commenter"] is True
        assert call_kwargs["commenter_options"] == {"route": True}

    def test_without_commenter(self, mock_instrumentor):
        engine = MagicMock(spec=[])
        instrument_engine(engine)
        call_kwargs = mock_instrumentor.instrument.call_args[1]
        assert "enable_commenter" not in call_kwargs


# ---------------------------------------------------------------------------
# uninstrument_engine
# ---------------------------------------------------------------------------


class TestUninstrumentEngine:
    def test_calls_uninstrument(self, mock_instrumentor):
        engine = MagicMock()
        uninstrument_engine(engine)
        mock_instrumentor.uninstrument.assert_called_once()

    def test_noop_when_not_installed(self):
        """Should not raise if opentelemetry is not installed."""
        import sys

        # Temporarily hide the real module so the import inside fails
        saved = sys.modules.pop("opentelemetry.instrumentation.sqlalchemy", None)
        sys.modules["opentelemetry.instrumentation.sqlalchemy"] = None  # type: ignore[assignment]
        try:
            uninstrument_engine(MagicMock())  # should silently succeed
        finally:
            if saved is not None:
                sys.modules["opentelemetry.instrumentation.sqlalchemy"] = saved
            else:
                sys.modules.pop("opentelemetry.instrumentation.sqlalchemy", None)


# ---------------------------------------------------------------------------
# configure_sqlalchemy_instrumentation
# ---------------------------------------------------------------------------


class TestConfigureGlobal:
    def test_instruments_globally(self, mock_instrumentor):
        configure_sqlalchemy_instrumentation(service_name="my-svc")
        mock_instrumentor.instrument.assert_called_once()

    def test_idempotent(self, mock_instrumentor):
        configure_sqlalchemy_instrumentation()
        configure_sqlalchemy_instrumentation()
        # Should only call instrument once
        mock_instrumentor.instrument.assert_called_once()

    def test_with_config_object(self, mock_instrumentor):
        cfg = SQLAlchemyInstrumentationConfig(
            service_name="audit-service",
            enable_commenter=True,
            commenter_options={"route": True},
        )
        configure_sqlalchemy_instrumentation(config=cfg)
        call_kwargs = mock_instrumentor.instrument.call_args[1]
        assert call_kwargs["enable_commenter"] is True
        assert call_kwargs["commenter_options"] == {"route": True}

    def test_reset_allows_reinstrumentation(self, mock_instrumentor):
        configure_sqlalchemy_instrumentation()
        reset_sqlalchemy_instrumentation()
        configure_sqlalchemy_instrumentation()
        assert mock_instrumentor.instrument.call_count == 2


# ---------------------------------------------------------------------------
# reset_sqlalchemy_instrumentation
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_calls_uninstrument(self, mock_instrumentor):
        configure_sqlalchemy_instrumentation()
        reset_sqlalchemy_instrumentation()
        mock_instrumentor.uninstrument.assert_called_once()

    def test_reset_noop_when_not_instrumented(self, mock_instrumentor):
        reset_sqlalchemy_instrumentation()
        mock_instrumentor.uninstrument.assert_not_called()
