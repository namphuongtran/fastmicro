from typing import Optional, Dict, Any, Type, TypeVar, List
from pathlib import Path
import os
import json
from pydantic import ValidationError

from .app_options import AppOptions
from .database_options import DatabaseOptions
from .logging_options import LoggingOptions
from .security_options import SecurityOptions
from .localization_options import LocalizationOptions
from .caching_options import CachingOptions
from .auth_options import AuthOptions

T = TypeVar('T')
"""SettingsManager is a centralized manager for application settings, allowing easy access and modification of configurations.
Advantages:

Lazy loading - only instantiate settings that are actually used
Lower memory footprint - don't create unused setting objects
Better performance - avoid initializing heavy settings (like database connections)
Flexible - users can selectively configure only what they need
Cleaner separation - each component manages its own settings
"""

class SettingsManager:
    """Centralized settings manager for all application configurations."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            env_file: Path to the environment file. Defaults to ".env"
        """
        self.env_file = env_file or ".env"
        self._settings_cache: Dict[Type, Any] = {}
        
        # Load all settings
        self.app = self.get_settings(AppOptions)
        self.auth = self.get_settings(AuthOptions)
        self.caching = self.get_settings(CachingOptions)
        self.database = self.get_settings(DatabaseOptions)
        self.localization = self.get_settings(LocalizationOptions)
        self.logging = self.get_settings(LoggingOptions)
        self.security = self.get_settings(SecurityOptions)
    
    def get_settings(self, settings_class: Type[T]) -> T:
        """
        Get settings instance for a specific settings class.
        
        Args:
            settings_class: The settings class to instantiate
            
        Returns:
            Instance of the settings class
        """
        if settings_class not in self._settings_cache:
            # Set the env_file for the settings class if it exists
            if hasattr(settings_class, 'model_config') and hasattr(settings_class.model_config, 'env_file'):
                settings_class.model_config.env_file = self.env_file
                
            self._settings_cache[settings_class] = settings_class()
            
        return self._settings_cache[settings_class]
    
    def reload_settings(self, settings_class: Optional[Type[T]] = None) -> None:
        """
        Reload settings from environment.
        
        Args:
            settings_class: Specific settings class to reload. If None, reload all.
        """
        if settings_class:
            if settings_class in self._settings_cache:
                del self._settings_cache[settings_class]
                # Reload the specific setting and update the corresponding attribute
                new_setting = self.get_settings(settings_class)
                self._update_attribute(settings_class, new_setting)
        else:
            self._settings_cache.clear()
            self.__init__(self.env_file)
    
    def _update_attribute(self, settings_class: Type, new_setting: Any) -> None:
        """Update the corresponding attribute when a setting is reloaded."""
        class_to_attr = {
            AppOptions: 'app',
            AuthOptions: 'auth',
            CachingOptions: 'caching',
            DatabaseOptions: 'database',
            LocalizationOptions: 'localization',
            LoggingOptions: 'logging',
            SecurityOptions: 'security'
        }
        
        attr_name = class_to_attr.get(settings_class)
        if attr_name:
            setattr(self, attr_name, new_setting)
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert all settings to a dictionary."""
        return {
            'app': self.app.model_dump(),
            'database': self.database.model_dump(),
            'logging': self.logging.model_dump(),
            'security': self.security.model_dump(exclude={'secret_key', 'jwt_secret_key', 'encryption_key'}),
            'localization': self.localization.model_dump(),
            'caching': self.caching.model_dump(exclude={'redis_password'}),
            'auth': self.auth.model_dump()
        }
    
    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all settings and return validation results.
        
        Returns:
            Dictionary with validation status for each settings group
        """
        validation_results = {}
        settings_map = {
            'app': (AppOptions, self.app),
            'auth': (AuthOptions, self.auth),
            'caching': (CachingOptions, self.caching),
            'database': (DatabaseOptions, self.database),
            'localization': (LocalizationOptions, self.localization),
            'logging': (LoggingOptions, self.logging),
            'security': (SecurityOptions, self.security)
        }
        
        for name, (settings_class, instance) in settings_map.items():
            try:
                # Try to create a new instance to validate current environment
                settings_class()
                validation_results[name] = {
                    'valid': True,
                    'errors': []
                }
            except ValidationError as e:
                validation_results[name] = {
                    'valid': False,
                    'errors': [str(error) for error in e.errors()]
                }
            except Exception as e:
                validation_results[name] = {
                    'valid': False,
                    'errors': [f"Unexpected error: {str(e)}"]
                }
        
        return validation_results
    
    def export_config(self, file_path: str, include_secrets: bool = False) -> None:
        """
        Export current configuration to a JSON file.
        
        Args:
            file_path: Path to export the configuration
            include_secrets: Whether to include sensitive information
        """
        config_data = self.to_dict() if not include_secrets else {
            'app': self.app.model_dump(),
            'database': self.database.model_dump(),
            'logging': self.logging.model_dump(),
            'security': self.security.model_dump(),
            'localization': self.localization.model_dump(),
            'caching': self.caching.model_dump(),
            'auth': self.auth.model_dump()
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
    
    def get_environment_status(self) -> Dict[str, Any]:
        """
        Get status of environment variables and configuration files.
        
        Returns:
            Dictionary with environment status information
        """
        return {
            'env_file': {
                'path': self.env_file,
                'exists': os.path.exists(self.env_file),
                'readable': os.path.exists(self.env_file) and os.access(self.env_file, os.R_OK)
            },
            'environment_variables': {
                key: '***' if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower()
                else os.getenv(key, 'Not set')
                for key in os.environ.keys()
                if any(prefix in key for prefix in ['APP_', 'DB_', 'CACHE_', 'AUTH_', 'LOG_', 'SECURITY_'])
            },
            'validation': self.validate_all()
        }
    
    def update_setting(self, setting_path: str, value: Any) -> bool:
        """
        Update a specific setting value.
        
        Args:
            setting_path: Dot notation path to the setting (e.g., 'app.name', 'database.host')
            value: New value for the setting
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            parts = setting_path.split('.')
            if len(parts) != 2:
                return False
                
            section, field = parts
            if not hasattr(self, section):
                return False
                
            setting_obj = getattr(self, section)
            if not hasattr(setting_obj, field):
                return False
                
            setattr(setting_obj, field, value)
            return True
            
        except Exception:
            return False
    
    def get_setting(self, setting_path: str) -> Any:
        """
        Get a specific setting value.
        
        Args:
            setting_path: Dot notation path to the setting (e.g., 'app.name', 'database.host')
            
        Returns:
            The setting value or None if not found
        """
        try:
            parts = setting_path.split('.')
            if len(parts) != 2:
                return None
                
            section, field = parts
            if not hasattr(self, section):
                return None
                
            setting_obj = getattr(self, section)
            return getattr(setting_obj, field, None)
            
        except Exception:
            return None