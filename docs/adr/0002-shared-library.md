# ADR-002: Shared Library Strategy

## Status
Accepted

## Date
2025-01

## Context
Multiple microservices need common functionality such as:
- Authentication/authorization utilities
- Database connection management
- Exception handling
- Logging and observability
- HTTP client utilities
- Validation helpers

We need to decide how to share this code effectively.

## Decision
We will maintain a monorepo with a shared library (`shared/`) that:

1. **Contains 16 modules** covering cross-cutting concerns
2. **Uses Poetry local dependencies** for development
3. **Can be published as a package** for external consumption

### Integration Pattern
Services reference the shared library via Poetry's path dependencies:

```toml
[tool.poetry.group.local.dependencies]
shared = { path = "../../shared", develop = true }
```

### Module Structure
```
shared/
├── auth/           # Authentication utilities
├── constants/      # Shared constants
├── dbs/            # Database abstractions
├── exceptions/     # Common exceptions
├── extensions/     # Framework extensions
├── proto/          # Protobuf definitions
└── utils/          # General utilities
```

## Consequences

### Positive
- Single source of truth for common code
- Easy updates propagate to all services
- Consistent behavior across services
- Reduced code duplication

### Negative
- Version coordination required
- Breaking changes affect all services
- Monorepo complexity

### Mitigations
- Semantic versioning for breaking changes
- Comprehensive test suite (945 tests)
- CI/CD validates shared library before service builds
