"""Configuration settings for Metastore Service."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    
    service_name: str = Field(default="metastore-service")
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    app_port: int = Field(default=8002, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/metastore_db")
    redis_url: str = Field(default="redis://localhost:6379/1")
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
