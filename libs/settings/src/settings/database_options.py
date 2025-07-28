from typing import Optional, Dict, Any
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseOptions(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Connection settings
    url: Optional[str] = Field(default=None, description="Complete database URL")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="ags_db", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    driver: str = Field(default="postgresql", description="Database driver")
    
    # Connection pool settings
    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, ge=-1, description="Pool recycle time in seconds")
    
    # Query settings
    echo: bool = Field(default=False, description="Echo SQL queries")
    echo_pool: bool = Field(default=False, description="Echo pool events")
    query_timeout: int = Field(default=30, ge=1, description="Query timeout in seconds")
    
    # Migration settings
    auto_migrate: bool = Field(default=False, description="Auto-run migrations on startup")
    migration_path: str = Field(default="migrations", description="Path to migration files")
    
    # SSL settings
    ssl_mode: Optional[str] = Field(default=None, description="SSL mode")
    ssl_cert: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA certificate path")
    
    # Additional connection parameters
    connect_args: Dict[str, Any] = Field(default_factory=dict, description="Additional connection arguments")
    
    @property
    def connection_url(self) -> str:
        """Generate connection URL from components."""
        if self.url:
            return self.url
        
        password_part = f":{self.password}" if self.password else ""
        return f"{self.driver}://{self.username}{password_part}@{self.host}:{self.port}/{self.name}"
    
    @model_validator(mode='after')
    def validate_driver(self):
        allowed_drivers = ['postgresql', 'mysql', 'sqlite', 'mssql', 'oracle']
        if self.driver not in allowed_drivers:
            raise ValueError(f'Driver must be one of: {allowed_drivers}')
        return self