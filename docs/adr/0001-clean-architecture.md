# ADR-001: Clean Architecture Pattern

## Status
Accepted

## Date
2025-01

## Context
We need a consistent architecture pattern for all Python microservices that:
- Separates business logic from infrastructure concerns
- Enables easy testing and mocking
- Supports dependency injection
- Allows for flexibility in database and messaging choices

## Decision
We will adopt Clean Architecture (also known as Hexagonal/Ports & Adapters) for all Python services with the following layer structure:

```
src/[service_name]/
├── api/                    # Presentation layer (FastAPI routes)
│   └── v1/                 # API versioning
├── application/            # Application services (use cases)
│   └── services/
├── domain/                 # Business logic (entities, interfaces)
│   ├── entities/
│   └── repositories/       # Repository interfaces (ports)
├── infrastructure/         # External adapters
│   ├── middleware/
│   └── persistence/        # Repository implementations
└── configs/                # Settings and configuration
```

### Key Principles
1. **Dependency Rule**: Dependencies point inward. Domain has no external dependencies.
2. **Interface Segregation**: Repository interfaces in domain, implementations in infrastructure.
3. **Dependency Injection**: Use FastAPI's `Depends()` for injecting implementations.

## Consequences

### Positive
- Clear separation of concerns
- Easy to test business logic in isolation
- Flexibility to swap infrastructure components
- Consistent structure across all services

### Negative
- More boilerplate code initially
- Learning curve for developers unfamiliar with the pattern
- Potential for over-engineering simple services

## Alternatives Considered

1. **Simple MVC**: Rejected due to tight coupling between layers
2. **Domain-Driven Design (full)**: Too complex for current scale
3. **No defined structure**: Would lead to inconsistency
