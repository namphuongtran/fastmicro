from typing import List, Dict, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalizationOptions(BaseSettings):
    """Localization and internationalization settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="LOCALIZATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Basic localization settings
    enabled: bool = Field(default=True, description="Enable localization")
    default_locale: str = Field(default="en", description="Default locale")
    supported_locales: List[str] = Field(
        default=["en", "vi", "ja", "ko", "zh"],
        description="Supported locales"
    )
    
    # Locale detection
    detect_from_header: bool = Field(default=True, description="Detect locale from Accept-Language header")
    detect_from_query: bool = Field(default=True, description="Detect locale from query parameter")
    detect_from_cookie: bool = Field(default=True, description="Detect locale from cookie")
    detect_from_subdomain: bool = Field(default=False, description="Detect locale from subdomain")
    
    # Parameter names
    query_parameter: str = Field(default="lang", description="Query parameter name for locale")
    cookie_name: str = Field(default="locale", description="Cookie name for locale")
    header_name: str = Field(default="Accept-Language", description="Header name for locale")
    
    # Translation files
    translations_directory: str = Field(default="locales", description="Directory containing translation files")
    translation_file_format: str = Field(default="json", description="Translation file format")
    fallback_locale: str = Field(default="en", description="Fallback locale if translation not found")
    
    # Formatting options
    date_format: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "%Y-%m-%d",
            "vi": "%d/%m/%Y",
            "ja": "%Y年%m月%d日",
            "ko": "%Y년 %m월 %d일",
            "zh": "%Y年%m月%d日"
        },
        description="Date format for each locale"
    )
    
    time_format: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "%H:%M:%S",
            "vi": "%H:%M:%S",
            "ja": "%H時%M分%S秒",
            "ko": "%H시 %M분 %S초",
            "zh": "%H时%M分%S秒"
        },
        description="Time format for each locale"
    )
    
    currency_format: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "en": {"symbol": "$", "position": "before"},
            "vi": {"symbol": "₫", "position": "after"},
            "ja": {"symbol": "¥", "position": "before"},
            "ko": {"symbol": "₩", "position": "before"},
            "zh": {"symbol": "¥", "position": "before"}
        },
        description="Currency format for each locale"
    )
    
    # Timezone settings
    default_timezone: str = Field(default="UTC", description="Default timezone")
    user_timezone_detection: bool = Field(default=True, description="Detect user timezone")
    
    @model_validator(mode='after')
    def validate_locale_format(self):
        # Validate default_locale
        if len(self.default_locale) < 2:
            raise ValueError('default_locale must be at least 2 characters long')
        self.default_locale = self.default_locale.lower()
        
        # Validate fallback_locale
        if len(self.fallback_locale) < 2:
            raise ValueError('fallback_locale must be at least 2 characters long')
        self.fallback_locale = self.fallback_locale.lower()
        
        return self

    @model_validator(mode='after')
    def validate_supported_locales(self):
        self.supported_locales = [locale.lower() for locale in self.supported_locales]
        return self