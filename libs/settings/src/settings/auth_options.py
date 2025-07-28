from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from enum import Enum

class AuthMethod(str, Enum):
    """Supported authentication methods."""
    OIDC = "oidc"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"    

class OIDCOptions(BaseSettings):
    """OpenID Connect authentication settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_OIDC_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(False, description="Enable OIDC authentication")
    issuer_url: Optional[str] = Field(None, description="OIDC issuer URL")
    client_id: Optional[str] = Field(None, description="OIDC client ID")
    client_secret: Optional[str] = Field(None, description="OIDC client secret")
    redirect_uri: Optional[str] = Field(None, description="OIDC redirect URI")
    scopes: List[str] = Field(
        default=["openid", "profile", "email"], 
        description="OIDC scopes to request"
    )
    audience: Optional[str] = Field(None, description="OIDC audience")
    discovery_cache_ttl: int = Field(3600, description="OIDC discovery cache TTL in seconds")
    
    @model_validator(mode='after')
    def validate_oidc_config(self):
        """Validate OIDC configuration when enabled."""
        if self.enabled:
            if not self.client_id:
                raise ValueError("OIDC client ID is required when OIDC is enabled")
            if not self.issuer_url:
                raise ValueError("OIDC issuer URL is required when OIDC is enabled")
        return self

class OAuth2Options(BaseSettings):
    """OAuth2 authentication settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_OAUTH2_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(False, description="Enable OAuth2 authentication")
    authorization_url: Optional[str] = Field(None, description="OAuth2 authorization URL")
    token_url: Optional[str] = Field(None, description="OAuth2 token URL")
    client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    client_secret: Optional[str] = Field(None, description="OAuth2 client secret")
    redirect_uri: Optional[str] = Field(None, description="OAuth2 redirect URI")
    scopes: List[str] = Field(default=[], description="OAuth2 scopes to request")
    state: bool = Field(True, description="Use state parameter for CSRF protection")
    pkce: bool = Field(True, description="Use PKCE for OAuth2")
    
    @model_validator(mode='after')
    def validate_oauth2_config(self):
        """Validate OAuth2 configuration when enabled."""
        if self.enabled:
            if not self.client_id:
                raise ValueError("OAuth2 client ID is required when OAuth2 is enabled")
            if not self.authorization_url:
                raise ValueError("OAuth2 authorization URL is required when OAuth2 is enabled")
            if not self.token_url:
                raise ValueError("OAuth2 token URL is required when OAuth2 is enabled")
        return self

class APIKeyOptions(BaseSettings):
    """API Key authentication settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_API_KEY_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(False, description="Enable API key authentication")
    header: str = Field("X-API-Key", description="API key header name")
    query_param: str = Field("api_key", description="API key query parameter name")
    location: str = Field("header", description="API key location: header, query, or both")
    prefix: Optional[str] = Field(None, description="API key prefix (e.g., 'Bearer')")
    validate_url: Optional[str] = Field(None, description="URL to validate API keys")
    cache_ttl: int = Field(300, description="API key validation cache TTL in seconds")

class AuthOptions(BaseSettings):
    """Authentication and authorization settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === GENERAL SETTINGS ===
    enabled: bool = Field(True, description="Enable authentication")
    method: AuthMethod = Field(AuthMethod.OIDC, description="Primary authentication method")
    
    # === AUTHENTICATION METHODS ===
    oidc: OIDCOptions = OIDCOptions()
    oauth2: OAuth2Options = OAuth2Options()
    api_key: APIKeyOptions = APIKeyOptions()