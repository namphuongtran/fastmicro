# Libs Directory

This directory contains **specialized, standalone Python packages** that are optional dependencies for services.

## Packages

| Package | Purpose | Used By |
|---------|---------|---------|
| `settings/` | Advanced configuration management with SettingsManager | `federation-gateway` |

## Difference from `shared/`

| Aspect | `shared/` | `libs/` |
|--------|-----------|---------|
| **Purpose** | Core enterprise library | Optional specialized packages |
| **Dependency** | Always installed | Install as needed |
| **Scope** | Cross-cutting concerns | Domain-specific utilities |
| **Examples** | Auth, Config, Observability, Exceptions | Settings Manager, Future: Email, SMS |

## When to Use Which

### Use `shared/` when:
- You need core functionality (auth, logging, exceptions)
- The feature is used by most services
- You want minimal dependencies

### Use `libs/` packages when:
- You need specialized functionality
- The feature is only used by specific services
- The package has additional dependencies

## Architecture Decision

See [ADR-0002: Shared Library](../docs/adr/0002-shared-library.md) for architectural rationale.

## Future Consolidation

There is overlap between `shared/config/` and `libs/settings/`. A future sprint will evaluate:
1. Merging `SettingsManager` pattern into `shared/config/`
2. Deprecating `libs/settings/` after migration
3. Updating `federation-gateway` to use `shared/config/`

Track progress: [GitHub Issue TBD]
