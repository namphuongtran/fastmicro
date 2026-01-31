# Settings Library

Advanced configuration management with centralized SettingsManager pattern.

## Overview

This package provides a `SettingsManager` class that centralizes all application configuration with:
- Lazy loading of settings
- Caching for performance  
- Type-safe access via Pydantic models
- Environment file support

## Usage

```python
from settings.settings_manager import SettingsManager

# Initialize settings manager
settings = SettingsManager(env_file=".env")

# Access settings
print(settings.app.name)
print(settings.database.connection_url)
print(settings.logging.level)
```

## Available Options

| Module | Description | Env Prefix |
|--------|-------------|------------|
| `app_options.py` | Application settings | `APP_` |
| `auth_options.py` | Authentication config | `AUTH_` |
| `caching_options.py` | Cache configuration | `CACHE_` |
| `database_options.py` | Database connections | `DATABASE_` |
| `localization_options.py` | i18n settings | `LOCALIZATION_` |
| `logging_options.py` | Logging configuration | `LOGGING_` |
| `security_options.py` | Security settings | `SECURITY_` |

## Comparison with `shared/config/`

| Feature | `libs/settings` | `shared/config` |
|---------|-----------------|-----------------|
| Pattern | Centralized Manager | Individual Settings |
| Loading | Eager (all at once) | Lazy (on demand) |
| Caching | Internal dict | `@lru_cache` |
| Best For | Gateway services | Microservices |

## Migration Plan

This package may be consolidated into `shared/config/` in a future release. See [libs/README.md](../README.md) for details.

## Development

```bash
# Install development dependencies
cd libs/settings
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/
```
