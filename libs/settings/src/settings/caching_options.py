from typing import Optional, List
from enum import Enum
from pydantic import Field, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class CacheBackend(str, Enum):
    REDIS = "redis"
    MEMCACHED = "memcached"
    MEMORY = "memory"
    DATABASE = "database"

class RedisOptions(BaseSettings):
    """Redis cache backend configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_REDIS_",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Connection settings
    url: Optional[str] = Field(default=None, description="Redis connection URL")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    ssl: bool = Field(default=False, description="Use SSL for Redis connection")
    
    # Connection pool settings
    max_connections: int = Field(default=10, description="Maximum Redis connections")
    retry_on_timeout: bool = Field(default=True, description="Retry on Redis timeout")
    socket_timeout: int = Field(default=5, description="Redis socket timeout")
    connection_timeout: int = Field(default=5, description="Redis connection timeout")
    
    @computed_field
    @property
    def connection_url(self) -> str:
        """Generate Redis connection URL."""
        if self.url:
            return self.url
                
        password_part = f":{self.password}@" if self.password else ""
        protocol = "rediss" if self.ssl else "redis"
        return f"{protocol}://{password_part}{self.host}:{self.port}/{self.db}"

class MemcachedOptions(BaseSettings):
    """Memcached cache backend configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_MEMCACHED_",
        case_sensitive=False,
        extra="ignore"
    )
    
    servers: List[str] = Field(default=["localhost:11211"], description="Memcached servers")

class MemoryOptions(BaseSettings):
    """In-memory cache backend configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_MEMORY_",
        case_sensitive=False,
        extra="ignore"
    )
    
    max_size: int = Field(default=128 * 1024 * 1024, description="Max memory cache size in bytes")
    ttl_check_interval: int = Field(default=60, description="TTL check interval for memory cache")

class DatabaseOptions(BaseSettings):
    """Database cache backend configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_DATABASE_",
        case_sensitive=False,
        extra="ignore"
    )
    
    table_name: str = Field(default="cache_entries", description="Cache table name")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval for expired entries")

class CacheStrategyOptions(BaseSettings):
    """Cache strategy and behavior configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_STRATEGY_",
        case_sensitive=False,
        extra="ignore"
    )
    
    key_prefix: str = Field(default="ags:", description="Cache key prefix")
    compress_data: bool = Field(default=True, description="Compress cached data")
    serialize_format: str = Field(default="pickle", description="Serialization format")
    default_ttl: int = Field(default=300, description="Default TTL in seconds")
    
    @model_validator(mode='after')
    def validate_serialize_format(self):
        allowed_formats = ['pickle', 'json', 'msgpack']
        if self.serialize_format not in allowed_formats:
            raise ValueError(f'serialize_format must be one of: {allowed_formats}')
        return self

class CacheWarmingOptions(BaseSettings):
    """Cache warming configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_WARMING_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=False, description="Enable cache warming on startup")
    batch_size: int = Field(default=100, description="Batch size for cache warming")
    warm_on_startup: bool = Field(default=False, description="Warm cache on application startup")

class ClusteringOptions(BaseSettings):
    """Distributed caching and clustering configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_CLUSTERING_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=False, description="Enable cache clustering")
    nodes: List[str] = Field(default_factory=list, description="Cluster node addresses")
    hash_ring_size: int = Field(default=1024, description="Consistent hash ring size")
    replication_factor: int = Field(default=2, description="Number of replicas per cache entry")

class MonitoringOptions(BaseSettings):
    """Cache monitoring and metrics configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_MONITORING_",
        case_sensitive=False,
        extra="ignore"
    )
    
    metrics_enabled: bool = Field(default=True, description="Enable cache metrics")
    log_operations: bool = Field(default=False, description="Log cache operations")
    stats_interval: int = Field(default=60, description="Statistics collection interval")
    export_prometheus: bool = Field(default=False, description="Export metrics to Prometheus")

class CachingOptions(BaseSettings):
    """Caching configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === GENERAL SETTINGS ===
    enabled: bool = Field(default=True, description="Enable caching")
    backend: CacheBackend = Field(default=CacheBackend.REDIS, description="Cache backend")
    
    # === BACKEND CONFIGURATIONS ===
    redis: RedisOptions = RedisOptions()
    memcached: MemcachedOptions = MemcachedOptions()
    memory: MemoryOptions = MemoryOptions()
    database: DatabaseOptions = DatabaseOptions()
    
    # === ADDITIONAL SETTINGS ===
    strategy: CacheStrategyOptions = CacheStrategyOptions()
    warming: CacheWarmingOptions = CacheWarmingOptions()
    clustering: ClusteringOptions = ClusteringOptions()
    monitoring: MonitoringOptions = MonitoringOptions()