from typing import Optional, List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class CryptoOptions(BaseSettings):
    """Cryptographic keys and encryption settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_CRYPTO_",
        case_sensitive=False,
        extra="ignore"
    )
    
    secret_key: Optional[str] = Field(default=None, description="Application secret key")
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    encryption_key: Optional[str] = Field(default=None, description="Encryption key")

class SecurityHeadersOptions(BaseSettings):
    """Security headers configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_HEADERS_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=True, description="Enable security headers")
    hsts_enabled: bool = Field(default=True, description="Enable HSTS header")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age")
    content_type_options: bool = Field(default=True, description="Enable X-Content-Type-Options")
    frame_options: str = Field(default="DENY", description="X-Frame-Options value")
    xss_protection: bool = Field(default=True, description="Enable XSS protection")
    
    @model_validator(mode='after')
    def validate_frame_options(self):
        allowed_values = ['DENY', 'SAMEORIGIN', 'ALLOW-FROM']
        if self.frame_options not in allowed_values:
            raise ValueError(f'frame_options must be one of: {allowed_values}')
        return self

class RateLimitOptions(BaseSettings):
    """Rate limiting configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_RATE_LIMIT_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=True, description="Enable rate limiting")
    requests: int = Field(default=100, description="Requests per time window")
    window: int = Field(default=60, description="Time window in seconds")
    by_ip: bool = Field(default=True, description="Rate limit by IP address")
    storage: str = Field("memory", description="Rate limit storage: memory, redis")
    redis_url: Optional[str] = Field(None, description="Redis URL for rate limiting")

class InputValidationOptions(BaseSettings):
    """Input validation and sanitization settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_INPUT_",
        case_sensitive=False,
        extra="ignore"
    )
    
    max_request_size: int = Field(default=16 * 1024 * 1024, description="Max request size")
    validate_json: bool = Field(default=True, description="Validate JSON input")
    sanitize_input: bool = Field(default=True, description="Sanitize user input")

class IPFilterOptions(BaseSettings):
    """IP filtering and access control settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_IP_",
        case_sensitive=False,
        extra="ignore"
    )
    
    allowed_ips: List[str] = Field(default_factory=list, description="Allowed IP addresses")
    blocked_ips: List[str] = Field(default_factory=list, description="Blocked IP addresses")

class SSLOptions(BaseSettings):
    """SSL/TLS configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_SSL_",
        case_sensitive=False,
        extra="ignore"
    )
    
    force_https: bool = Field(default=False, description="Force HTTPS redirects")
    redirect: bool = Field(default=False, description="Redirect HTTP to HTTPS")

class CORSOptions(BaseSettings):
    """CORS (Cross-Origin Resource Sharing) configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_CORS_",
        case_sensitive=False,
        extra="ignore"
    )
    
    enabled: bool = Field(default=True, description="Enable CORS")
    allow_origins: List[str] = Field(default=["*"], description="Allowed origins")
    allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
        description="Allowed HTTP methods"
    )
    allow_headers: List[str] = Field(
        default=["Authorization", "Content-Type", "X-Requested-With"], 
        description="Allowed headers"
    )
    expose_headers: List[str] = Field(default_factory=list, description="Headers to expose to client")
    allow_credentials: bool = Field(default=True, description="Allow credentials")
    max_age: int = Field(default=86400, description="Preflight cache max age in seconds")

class SessionSecurityOptions(BaseSettings):
    """Session security configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_SESSION_",
        case_sensitive=False,
        extra="ignore"
    )
    
    timeout: int = Field(default=3600, description="Session timeout in seconds")
    secure_cookies: bool = Field(default=True, description="Use secure cookies")
    same_site_cookies: str = Field(default="lax", description="SameSite cookie policy")
    
    @model_validator(mode='after')
    def validate_same_site_cookies(self):
        allowed_values = ['strict', 'lax', 'none']
        if self.same_site_cookies.lower() not in allowed_values:
            raise ValueError(f'same_site_cookies must be one of: {allowed_values}')
        self.same_site_cookies = self.same_site_cookies.lower()
        return self

class SecurityOptions(BaseSettings):
    """Security configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === SECURITY COMPONENTS ===
    crypto: CryptoOptions = CryptoOptions()
    headers: SecurityHeadersOptions = SecurityHeadersOptions()
    cors: CORSOptions = CORSOptions()
    rate_limit: RateLimitOptions = RateLimitOptions()
    input_validation: InputValidationOptions = InputValidationOptions()
    ip_filter: IPFilterOptions = IPFilterOptions()
    ssl: SSLOptions = SSLOptions()
    session: SessionSecurityOptions = SessionSecurityOptions()