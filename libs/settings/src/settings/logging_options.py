from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class LogFormat(str, Enum):
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class ConsoleOptions(BaseModel):
    """Console logging configuration."""
    
    enabled: bool = Field(default=True, description="Enable console logging")
    level: Optional[LogLevel] = Field(default=None, description="Console log level (inherits global if None)")
    format: Optional[LogFormat] = Field(default=None, description="Console log format (inherits global if None)")
    colorize: bool = Field(default=True, description="Enable colored output")
    show_timestamp: bool = Field(default=True, description="Show timestamp in console logs")
    show_level: bool = Field(default=True, description="Show log level in console")
    show_logger_name: bool = Field(default=True, description="Show logger name in console")


class FileOptions(BaseModel):
    """File logging configuration."""
    
    enabled: bool = Field(default=False, description="Enable file logging")
    level: Optional[LogLevel] = Field(default=None, description="File log level (inherits global if None)")
    format: Optional[LogFormat] = Field(default=None, description="File log format (inherits global if None)")
    path: str = Field(default="logs/app.log", description="Log file path")
    max_size: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files")
    rotation_time: Optional[str] = Field(default=None, description="Time-based rotation (e.g., 'midnight', 'H')")
    encoding: str = Field(default="utf-8", description="File encoding")
    buffer_size: int = Field(default=8192, description="File buffer size")


class SentryOptions(BaseModel):
    """Sentry logging configuration."""
    
    enabled: bool = Field(default=False, description="Enable Sentry integration")
    dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    environment: str = Field(default="development", description="Sentry environment")
    release: Optional[str] = Field(default=None, description="Application release version")
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Error sampling rate")
    traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Performance sampling rate")
    debug: bool = Field(default=False, description="Enable Sentry debug mode")
    attach_stacktrace: bool = Field(default=True, description="Attach stack traces to messages")
    send_default_pii: bool = Field(default=False, description="Send personally identifiable information")
    max_breadcrumbs: int = Field(default=100, description="Maximum number of breadcrumbs")
    before_send: Optional[str] = Field(default=None, description="Before send callback function name")


class OpenTelemetryOptions(BaseModel):
    """OpenTelemetry logging configuration."""
    
    enabled: bool = Field(default=False, description="Enable OpenTelemetry integration")
    endpoint: Optional[str] = Field(default=None, description="OTLP endpoint URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")
    service_name: str = Field(default="ags-service", description="Service name")
    service_version: Optional[str] = Field(default=None, description="Service version")
    resource_attributes: Dict[str, str] = Field(default_factory=dict, description="Resource attributes")
    export_timeout: int = Field(default=30, description="Export timeout in seconds")
    export_batch_size: int = Field(default=512, description="Batch size for exports")
    export_schedule_delay: int = Field(default=5000, description="Schedule delay in milliseconds")


class ElasticSearchOptions(BaseModel):
    """ElasticSearch logging configuration."""
    
    enabled: bool = Field(default=False, description="Enable ElasticSearch logging")
    hosts: List[str] = Field(default=["localhost:9200"], description="ElasticSearch hosts")
    index_name: str = Field(default="logs", description="Index name pattern")
    index_template: Optional[str] = Field(default=None, description="Index template")
    username: Optional[str] = Field(default=None, description="ElasticSearch username")
    password: Optional[str] = Field(default=None, description="ElasticSearch password")
    use_ssl: bool = Field(default=False, description="Use SSL connection")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Connection timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    buffer_size: int = Field(default=1000, description="Buffer size before bulk insert")
    flush_interval: int = Field(default=5, description="Flush interval in seconds")


class RequestLoggingOptions(BaseModel):
    """HTTP request logging configuration."""
    
    enabled: bool = Field(default=True, description="Enable request logging")
    log_request_body: bool = Field(default=False, description="Log request body")
    log_response_body: bool = Field(default=False, description="Log response body")
    log_headers: bool = Field(default=False, description="Log request/response headers")
    log_query_params: bool = Field(default=True, description="Log query parameters")
    log_user_agent: bool = Field(default=True, description="Log user agent")
    log_ip_address: bool = Field(default=True, description="Log client IP address")
    ignore_patterns: List[str] = Field(
        default_factory=lambda: ["/health", "/metrics", "/favicon.ico"],
        description="URL patterns to ignore in request logging"
    )
    ignore_methods: List[str] = Field(
        default_factory=lambda: ["OPTIONS"],
        description="HTTP methods to ignore in request logging"
    )
    max_body_size: int = Field(default=1024, description="Maximum body size to log in bytes")
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive data in logs")
    sensitive_fields: List[str] = Field(
        default_factory=lambda: ["password", "token", "secret", "key", "authorization"],
        description="Fields to mask in logs"
    )


class LoggingOptions(BaseSettings):
    """Logging configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="LOGGING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Global logging settings
    level: LogLevel = Field(default=LogLevel.INFO, description="Global log level")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Global log format")
    use_request_logger: bool = Field(default=True, description="Enable request logging middleware")
    
    # Structured logging options
    include_timestamp: bool = Field(default=True, description="Include timestamp in logs")
    include_level: bool = Field(default=True, description="Include log level")
    include_logger_name: bool = Field(default=True, description="Include logger name")
    include_module: bool = Field(default=False, description="Include module name")
    include_function: bool = Field(default=False, description="Include function name")
    include_line_number: bool = Field(default=False, description="Include line number")
    include_process_id: bool = Field(default=False, description="Include process ID")
    include_thread_id: bool = Field(default=False, description="Include thread ID")
    
    # Provider-specific configurations
    console: ConsoleOptions = Field(default_factory=ConsoleOptions, description="Console logging options")
    file: FileOptions = Field(default_factory=FileOptions, description="File logging options")
    sentry: SentryOptions = Field(default_factory=SentryOptions, description="Sentry logging options")
    open_telemetry: OpenTelemetryOptions = Field(default_factory=OpenTelemetryOptions, description="OpenTelemetry options")
    elasticsearch: ElasticSearchOptions = Field(default_factory=ElasticSearchOptions, description="ElasticSearch options")
    request_logging: RequestLoggingOptions = Field(default_factory=RequestLoggingOptions, description="Request logging options")
    
    # Logger-specific configurations
    loggers: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "uvicorn": {"level": "INFO"},
            "uvicorn.access": {"level": "INFO"},
            "fastapi": {"level": "INFO"},
            "sqlalchemy": {"level": "WARNING"},
            "httpx": {"level": "INFO"},
            "asyncio": {"level": "WARNING"}
        },
        description="Logger-specific configurations"
    )
    
    # Performance settings
    async_logging: bool = Field(default=False, description="Enable asynchronous logging")
    queue_size: int = Field(default=1000, description="Async logging queue size")
    
    def get_effective_level(self, provider_level: Optional[LogLevel] = None) -> LogLevel:
        """Get the effective log level for a provider."""
        return provider_level or self.level
    
    def get_effective_format(self, provider_format: Optional[LogFormat] = None) -> LogFormat:
        """Get the effective log format for a provider."""
        return provider_format or self.format