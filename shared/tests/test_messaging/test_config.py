"""Tests for shared.messaging.config — RabbitMQ and Kafka settings."""

from shared.messaging.config import KafkaSettings, RabbitMQSettings


class TestRabbitMQSettings:
    """Tests for RabbitMQSettings defaults and URL construction."""

    def test_default_values(self):
        """Test default settings without environment variables."""
        settings = RabbitMQSettings()
        assert settings.host == "localhost"
        assert settings.port == 5672
        assert settings.username == "guest"
        assert settings.vhost == "/"
        assert settings.ssl is False
        assert settings.prefetch_count == 10
        assert settings.exchange_name == "domain.events"
        assert settings.dead_letter_exchange == "domain.events.dlx"

    def test_url_property_default(self):
        """Test URL generation with default values."""
        settings = RabbitMQSettings()
        url = settings.url
        assert url == "amqp://guest:guest@localhost:5672/"

    def test_url_property_with_ssl(self):
        """Test URL uses amqps scheme when SSL enabled."""
        settings = RabbitMQSettings(ssl=True)
        assert settings.url.startswith("amqps://")

    def test_url_property_with_custom_vhost(self):
        """Test URL includes custom vhost."""
        settings = RabbitMQSettings(vhost="/myapp")
        assert settings.url.endswith("/myapp")

    def test_url_property_with_custom_credentials(self):
        """Test URL includes custom credentials."""
        settings = RabbitMQSettings(host="broker", port=5673, username="admin")
        assert "admin:" in settings.url
        assert "broker:5673" in settings.url


class TestKafkaSettings:
    """Tests for KafkaSettings defaults and parsing."""

    def test_default_values(self):
        """Test default settings without environment variables."""
        settings = KafkaSettings()
        assert settings.bootstrap_servers == "localhost:9092"
        assert settings.client_id == "fastmicro"
        assert settings.acks == "all"
        assert settings.compression_type == "gzip"
        assert settings.security_protocol == "PLAINTEXT"
        assert settings.sasl_mechanism is None
        assert settings.group_id == "fastmicro-default"

    def test_bootstrap_servers_list_single(self):
        """Test parsing single bootstrap server."""
        settings = KafkaSettings()
        assert settings.bootstrap_servers_list == ["localhost:9092"]

    def test_bootstrap_servers_list_multiple(self):
        """Test parsing multiple bootstrap servers."""
        settings = KafkaSettings(bootstrap_servers="broker1:9092, broker2:9092, broker3:9092")
        assert settings.bootstrap_servers_list == [
            "broker1:9092",
            "broker2:9092",
            "broker3:9092",
        ]
