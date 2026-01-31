# Metastore Service

Metadata management service for storing and managing application metadata, configurations, and feature flags.

## Overview

The Metastore Service provides centralized metadata management for the microservices architecture. It handles application configurations, feature flags, tenant settings, and dynamic configurations.

## Features

- **Metadata Storage**: Store and retrieve application metadata
- **Feature Flags**: Dynamic feature flag management
- **Configuration Management**: Centralized configuration for services
- **Tenant Settings**: Multi-tenant configuration support
- **Version Control**: Track configuration changes with versioning
- **Real-time Updates**: WebSocket support for configuration changes

## Architecture

```
src/metastore_service/
├── api/v1/                 # API controllers
├── application/services/   # Business logic
├── domain/entities/        # Domain models
├── domain/repositories/    # Repository interfaces
├── infrastructure/         # External concerns
└── configs/               # Settings
```

## Getting Started

```bash
cd services/metastore-service
poetry install
poetry run uvicorn metastore_service.main:app --reload --port 8002
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| POST | `/api/v1/metadata` | Create metadata entry |
| GET | `/api/v1/metadata` | List metadata entries |
| GET | `/api/v1/metadata/{key}` | Get metadata by key |
| PUT | `/api/v1/metadata/{key}` | Update metadata |
| DELETE | `/api/v1/metadata/{key}` | Delete metadata |
| GET | `/api/v1/features` | List feature flags |
| GET | `/api/v1/features/{name}` | Get feature flag status |

## License

MIT License
