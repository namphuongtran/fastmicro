"""Tests for structlog configuration."""

import pytest

from shared.observability import (
    Environment,
    LoggingConfig,
    bind_contextvars,
    clear_contextvars,
    clear_correlation_id,
    configure_structlog,
    configure_structlog_for_testing,
    generate_correlation_id,
    get_correlation_id,
    get_structlog_logger,
    reset_structlog_configuration,
    set_correlation_id,
)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset structlog configuration before each test."""
    reset_structlog_configuration()
    clear_correlation_id()
    clear_contextvars()
    yield
    reset_structlog_configuration()
    clear_correlation_id()
    clear_contextvars()


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig(service_name="test-service")

        assert config.service_name == "test-service"
        assert config.environment == "development"
        assert config.log_level == "INFO"
        assert config.json_logs is None
        assert config.add_caller_info is True
        assert config.add_timestamp is True
        assert config.utc_timestamps is True

    def test_is_development(self):
        """Test development environment detection."""
        assert LoggingConfig(service_name="test", environment="development").is_development
        assert LoggingConfig(service_name="test", environment="dev").is_development
        assert LoggingConfig(service_name="test", environment="local").is_development
        assert not LoggingConfig(service_name="test", environment="production").is_development

    def test_is_production(self):
        """Test production environment detection."""
        assert LoggingConfig(service_name="test", environment="production").is_production
        assert LoggingConfig(service_name="test", environment="prod").is_production
        assert not LoggingConfig(service_name="test", environment="development").is_production

    def test_is_testing(self):
        """Test testing environment detection."""
        assert LoggingConfig(service_name="test", environment="testing").is_testing
        assert LoggingConfig(service_name="test", environment="test").is_testing
        assert not LoggingConfig(service_name="test", environment="production").is_testing

    def test_should_use_json_auto_detect(self):
        """Test JSON output auto-detection."""
        # Development should use console
        assert not LoggingConfig(service_name="test", environment="development").should_use_json
        # Testing should use console
        assert not LoggingConfig(service_name="test", environment="testing").should_use_json
        # Production should use JSON
        assert LoggingConfig(service_name="test", environment="production").should_use_json
        # Staging should use JSON
        assert LoggingConfig(service_name="test", environment="staging").should_use_json

    def test_should_use_json_explicit(self):
        """Test explicit JSON configuration."""
        # Force JSON in development
        assert LoggingConfig(
            service_name="test", environment="development", json_logs=True
        ).should_use_json
        # Force console in production
        assert not LoggingConfig(
            service_name="test", environment="production", json_logs=False
        ).should_use_json


class TestConfigureStructlog:
    """Tests for configure_structlog function."""

    def test_basic_configuration(self):
        """Test basic structlog configuration."""
        configure_structlog(
            LoggingConfig(
                service_name="test-service",
                environment="testing",
            )
        )

        logger = get_structlog_logger("test")
        assert logger is not None

    def test_logger_has_service_context(self, capsys):
        """Test that logger includes service name."""
        configure_structlog(
            LoggingConfig(
                service_name="my-test-service",
                environment="development",
            )
        )

        logger = get_structlog_logger("test")
        logger.info("test message")

        captured = capsys.readouterr()
        assert "my-test-service" in captured.out or "my-test-service" in captured.err


class TestCorrelationId:
    """Tests for correlation ID management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("test-correlation-123")
        assert get_correlation_id() == "test-correlation-123"

    def test_generate_correlation_id(self):
        """Test generating correlation ID."""
        cid = generate_correlation_id()
        assert cid is not None
        assert len(cid) == 36  # UUID format

        # Each call generates a unique ID
        cid2 = generate_correlation_id()
        assert cid != cid2

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

        clear_correlation_id()
        assert get_correlation_id() is None


class TestContextVars:
    """Tests for context variable binding."""

    def test_bind_and_clear_contextvars(self, capsys):
        """Test binding context variables."""
        configure_structlog_for_testing()

        bind_contextvars(user_id="user-123", request_id="req-456")

        logger = get_structlog_logger("test")
        logger.info("test with context")

        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Context vars should appear in output
        assert "user-123" in output or "user_id" in output

        clear_contextvars()


class TestGetStructlogLogger:
    """Tests for get_structlog_logger function."""

    def test_get_logger_with_name(self):
        """Test getting logger with name."""
        configure_structlog_for_testing()

        logger = get_structlog_logger("my.module")
        assert logger is not None

    def test_get_logger_with_initial_context(self, capsys):
        """Test getting logger with initial context binding."""
        configure_structlog_for_testing()

        logger = get_structlog_logger("test", component="auth", version="1.0")
        logger.info("test message")

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "auth" in output or "component" in output


class TestEnvironmentEnum:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"
