# libs/settings/src/settings/validators.py
"""Settings validation utilities for your existing SettingsManager"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Import your existing SettingsManager and option classes
from .settings_manager import SettingsManager
from .app_options import AppOptions
from .database_options import DatabaseOptions
from .logging_options import LoggingOptions
from .security_options import SecurityOptions
from .localization_options import LocalizationOptions
from .caching_options import CachingOptions
from .auth_options import AuthOptions

logger = logging.getLogger(__name__)

class SettingsValidator:
    """Comprehensive settings validation for your SettingsManager"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager
    
    def validate_environment_file(self) -> Dict[str, Any]:
        """Validate the environment file exists and is readable"""
        env_path = Path(self.settings.env_file)
        
        result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'info': {
                'path': str(env_path),
                'exists': env_path.exists(),
                'readable': False,
                'size': 0
            }
        }
        
        if not env_path.exists():
            result['warnings'].append(f"Environment file '{env_path}' does not exist - using defaults")
            # Not necessarily an error since your settings have defaults
        else:
            result['info']['readable'] = os.access(env_path, os.R_OK)
            result['info']['size'] = env_path.stat().st_size
            
            if not result['info']['readable']:
                result['valid'] = False
                result['errors'].append(f"Environment file '{env_path}' is not readable")
            
            if result['info']['size'] == 0:
                result['warnings'].append(f"Environment file '{env_path}' is empty")
        
        return result
    
    def validate_required_production_vars(self) -> Dict[str, Any]:
        """Validate that production-critical variables are set properly"""
        critical_vars = {
            'SECURITY_SECRET_KEY': 'Security secret key must be set for production',
            'DB_PASSWORD': 'Database password should be set for production',
        }
        
        result = {
            'valid': True,
            'missing_critical': [],
            'warnings': [],
            'production_ready': True
        }
        
        for var, message in critical_vars.items():
            value = os.getenv(var, '')
            if not value:
                result['missing_critical'].append(var)
                result['warnings'].append(message)
            elif value in ['your-secret-key', 'your-password-here', 'changeme']:
                result['production_ready'] = False
                result['warnings'].append(f"{var} is using a default/placeholder value")
        
        # Check debug mode
        if os.getenv('APP_DEBUG', '').lower() == 'true':
            result['warnings'].append("Debug mode is enabled - disable for production")
            result['production_ready'] = False
        
        return result
    
    def validate_settings_values(self) -> Dict[str, Any]:
        """Validate the actual settings values make sense"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Validate app settings
            if hasattr(self.settings.app, 'port'):
                if self.settings.app.port < 1 or self.settings.app.port > 65535:
                    result['valid'] = False
                    result['errors'].append(f"Invalid app port number: {self.settings.app.port}")
            
            # Validate database settings
            if hasattr(self.settings.database, 'port'):
                if self.settings.database.port < 1 or self.settings.database.port > 65535:
                    result['valid'] = False
                    result['errors'].append(f"Invalid database port: {self.settings.database.port}")
            
            # Validate logging level if it exists
            if hasattr(self.settings.logging, 'level'):
                valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if self.settings.logging.level.upper() not in valid_log_levels:
                    result['valid'] = False
                    result['errors'].append(f"Invalid log level: {self.settings.logging.level}")
            
            # Validate cache settings
            if hasattr(self.settings.caching, 'ttl'):
                if self.settings.caching.ttl <= 0:
                    result['warnings'].append("Cache TTL is 0 or negative - caching will be ineffective")
            
            # Validate auth token expiration
            if hasattr(self.settings.auth, 'token_expire_minutes'):
                if self.settings.auth.token_expire_minutes <= 0:
                    result['valid'] = False
                    result['errors'].append("Token expiration must be positive")
                    
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Error validating settings values: {str(e)}")
        
        return result
    
    def full_validation(self) -> Dict[str, Any]:
        """Perform comprehensive validation using your existing validate_all method"""
        env_validation = self.validate_environment_file()
        production_validation = self.validate_required_production_vars()
        values_validation = self.validate_settings_values()
        
        # Use your existing validation method
        pydantic_validation = self.settings.validate_all()
        
        # Combine all validations
        overall_valid = (
            env_validation['valid'] and 
            values_validation['valid'] and
            all(result['valid'] for result in pydantic_validation.values())
        )
        
        return {
            'overall_valid': overall_valid,
            'production_ready': production_validation['production_ready'],
            'environment_file': env_validation,
            'production_settings': production_validation,
            'values_validation': values_validation,
            'pydantic_validation': pydantic_validation,
            'summary': self._create_validation_summary(
                env_validation, production_validation, values_validation, pydantic_validation
            )
        }
    
    def _create_validation_summary(self, env_val, prod_val, values_val, pydantic_val) -> Dict[str, Any]:
        """Create a summary of all validation results"""
        total_errors = (
            len(env_val.get('errors', [])) +
            len(values_val.get('errors', [])) +
            sum(len(result.get('errors', [])) for result in pydantic_val.values())
        )
        
        total_warnings = (
            len(env_val.get('warnings', [])) +
            len(prod_val.get('warnings', [])) +
            len(values_val.get('warnings', []))
        )
        
        return {
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'status': 'valid' if total_errors == 0 else 'invalid',
            'production_status': 'ready' if prod_val['production_ready'] and total_errors == 0 else 'not_ready'
        }

def validate_settings_cli():
    """Command-line validation function"""
    print("🔍 Validating settings configuration...")
    
    try:
        # Use your existing SettingsManager
        settings = SettingsManager()
        validator = SettingsValidator(settings)
        
        # Get validation results
        validation_results = validator.full_validation()
        
        print(f"Overall Status: {'✅ VALID' if validation_results['overall_valid'] else '❌ INVALID'}")
        print(f"Production Ready: {'✅ YES' if validation_results['production_ready'] else '⚠️  NO'}")
        
        # Show summary
        summary = validation_results['summary']
        if summary['total_errors'] > 0:
            print(f"\n❌ Found {summary['total_errors']} errors")
        if summary['total_warnings'] > 0:
            print(f"⚠️  Found {summary['total_warnings']} warnings")
        
        # Show detailed errors
        if validation_results['environment_file']['errors']:
            print("\n📁 Environment File Errors:")
            for error in validation_results['environment_file']['errors']:
                print(f"  • {error}")
        
        if validation_results['values_validation']['errors']:
            print("\n⚙️  Configuration Value Errors:")
            for error in validation_results['values_validation']['errors']:
                print(f"  • {error}")
        
        # Show Pydantic validation errors from your existing method
        for section, result in validation_results['pydantic_validation'].items():
            if not result['valid']:
                print(f"\n📋 {section.upper()} Settings Errors:")
                for error in result['errors']:
                    print(f"  • {error}")
        
        # Show warnings
        all_warnings = (
            validation_results['environment_file'].get('warnings', []) +
            validation_results['production_settings'].get('warnings', []) +
            validation_results['values_validation'].get('warnings', [])
        )
        
        if all_warnings:
            print(f"\n⚠️  Warnings:")
            for warning in all_warnings:
                print(f"  • {warning}")
        
        return validation_results['overall_valid']
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

# Health checker that works with your existing SettingsManager
class SettingsHealthChecker:
    """Health check utilities using your existing SettingsManager"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager
        self.validator = SettingsValidator(settings_manager)
    
    def quick_health_check(self) -> Dict[str, Any]:
        """Quick health check using your existing methods"""
        try:
            # Use your existing validate_all method
            validation = self.settings.validate_all()
            env_status = self.settings.get_environment_status()
            
            errors = sum(len(result.get('errors', [])) for result in validation.values())
            
            return {
                'status': 'healthy' if errors == 0 else 'unhealthy',
                'errors': errors,
                'env_file_exists': env_status['env_file']['exists'],
                'details': {
                    'validation_results': validation,
                    'environment_status': env_status
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

if __name__ == "__main__":
    success = validate_settings_cli()
    sys.exit(0 if success else 1)