from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class PaginationOptions(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_PAGINATION_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=True, description="Enable pagination")
    default_page_size: int = Field(default=20, description="Default page size")
    max_page_size: int = Field(default=100, description="Maximum page size")
    page_size_query_param: str = Field(default="page_size", description="Page size query parameter")
    page_query_param: str = Field(default="page", description="Page query parameter")

class AppOptions(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Basic app info
    name: str = Field(default="AGS APIs", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    description: Optional[str] = Field(default=None, description="Application description")
    
    # Server configuration
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=44381, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    
    # API configuration
    root_path: str = Field(default="/", description="API root path")   
    
    # Feature flags
    health_checks_enabled: bool = Field(default=True, description="Enable health checks")
    use_graphql: bool = Field(default=True, description="Enable GraphQL endpoint")
    use_restful: bool = Field(default=True, description="Enable REST API endpoints")

    pagination: PaginationOptions = PaginationOptions()
    
    @model_validator(mode='after')
    def validate_port(self):
        if not (1 <= self.port <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return self

    @model_validator(mode='after')
    def validate_root_path(self):
        if not self.root_path.startswith('/'):
            self.root_path = '/' + self.root_path
        self.root_path = self.root_path.rstrip('/')
        return self