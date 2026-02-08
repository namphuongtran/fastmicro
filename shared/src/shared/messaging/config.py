"""Messaging configuration settings.

Pydantic-based settings for RabbitMQ and Kafka connections,
following the same pattern as shared.config.redis and shared.config.database.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
    """RabbitMQ connection settings.

    Supports standalone and clustered RabbitMQ with SSL,
    prefetch control, and exchange/queue configuration.

    Attributes:
        host: RabbitMQ server host.
        port: AMQP port.
        username: Connection username.
        password: Connection password.
        vhost: Virtual host.
        ssl: Enable SSL/TLS.
        prefetch_count: Per-consumer prefetch limit.
        connection_timeout: Connection timeout in seconds.
        heartbeat: Heartbeat interval in seconds.
        exchange_name: Default exchange name for domain events.
        dead_letter_exchange: Dead letter exchange name.

    Example:
        >>> settings = RabbitMQSettings()
        >>> print(settings.url)
        amqp://guest:guest@localhost:5672/
    """

    model_config = SettingsConfigDict(
        env_prefix="RABBITMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="RabbitMQ host")
    port: int = Field(default=5672, ge=1, le=65535, description="AMQP port")
    username: str = Field(default="guest", description="Username")
    password: SecretStr = Field(default=SecretStr("guest"), description="Password")
    vhost: str = Field(default="/", description="Virtual host")
    ssl: bool = Field(default=False, description="Enable SSL/TLS")
    prefetch_count: int = Field(
        default=10,
        ge=1,
        le=10000,
        description="Per-consumer prefetch limit",
    )
    connection_timeout: int = Field(
        default=30,
        ge=1,
        description="Connection timeout in seconds",
    )
    heartbeat: int = Field(
        default=60,
        ge=0,
        description="Heartbeat interval (0 to disable)",
    )
    exchange_name: str = Field(
        default="domain.events",
        description="Default topic exchange for domain events",
    )
    dead_letter_exchange: str = Field(
        default="domain.events.dlx",
        description="Dead letter exchange name",
    )

    @property
    def url(self) -> str:
        """Build AMQP connection URL.

        Returns:
            AMQP URL string with credentials.
        """
        scheme = "amqps" if self.ssl else "amqp"
        pwd = self.password.get_secret_value()
        vhost = self.vhost.lstrip("/") or ""
        return f"{scheme}://{self.username}:{pwd}@{self.host}:{self.port}/{vhost}"


class KafkaSettings(BaseSettings):
    """Apache Kafka connection settings.

    Supports single-broker and cluster configurations
    with SASL authentication and SSL.

    Attributes:
        bootstrap_servers: Comma-separated broker addresses.
        client_id: Client identifier for Kafka connections.
        acks: Producer acknowledgement level.
        compression_type: Message compression (none, gzip, snappy, lz4, zstd).
        max_batch_size: Maximum batch size in bytes.
        linger_ms: Time to wait for batching in milliseconds.
        security_protocol: Security protocol (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL).
        sasl_mechanism: SASL mechanism when using SASL protocols.
        sasl_username: SASL username.
        sasl_password: SASL password.
        group_id: Default consumer group id.

    Example:
        >>> settings = KafkaSettings()
        >>> print(settings.bootstrap_servers)
        localhost:9092
    """

    model_config = SettingsConfigDict(
        env_prefix="KAFKA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated broker addresses",
    )
    client_id: str = Field(
        default="fastmicro",
        description="Client identifier",
    )
    acks: str = Field(
        default="all",
        description="Producer ack level: 0, 1, or all",
    )
    compression_type: str = Field(
        default="gzip",
        description="Compression: none, gzip, snappy, lz4, zstd",
    )
    max_batch_size: int = Field(
        default=16384,
        ge=0,
        description="Max batch size in bytes",
    )
    linger_ms: int = Field(
        default=10,
        ge=0,
        description="Time to wait for batching (ms)",
    )
    security_protocol: str = Field(
        default="PLAINTEXT",
        description="Security protocol",
    )
    sasl_mechanism: str | None = Field(
        default=None,
        description="SASL mechanism (PLAIN, SCRAM-SHA-256, etc.)",
    )
    sasl_username: str | None = Field(default=None, description="SASL username")
    sasl_password: SecretStr | None = Field(default=None, description="SASL password")
    group_id: str = Field(
        default="fastmicro-default",
        description="Default consumer group id",
    )

    @property
    def bootstrap_servers_list(self) -> list[str]:
        """Parse bootstrap servers into a list.

        Returns:
            List of broker address strings.
        """
        return [s.strip() for s in self.bootstrap_servers.split(",")]
