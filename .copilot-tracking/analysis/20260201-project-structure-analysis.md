# Project Structure Analysis

**Date:** 2026-02-01  
**Analyst:** GitHub Copilot (Claude Opus 4.5)

---

## 1. Root `.venv` Folder Analysis

### Current State
- `.venv` folder **exists** at project root
- Contains a Poetry-managed virtual environment (Python 3.x)
- Has its own `.gitignore` file that ignores all content (`*`)
- **NOT tracked in git** (0 files tracked, confirmed via `git ls-files`)
- Listed in root `.gitignore` (line 155: `.venv`)

### Recommendation: ✅ KEEP (No Action Required)

The `.venv` folder is:
1. **Already gitignored** - not polluting the repository
2. **Standard Poetry practice** - Poetry creates `.venv` when `virtualenvs-in-project = true`
3. **Useful for local development** - VS Code Python extension auto-detects it

**No removal needed** - it's working correctly as a local-only development artifact.

---

## 2. Monitoring Folder Location

### Current Structure
```
fastmicro/
├── infrastructure/           # DevOps, deployment, CI/CD
│   ├── k8s/
│   │   └── grafana/         # ⚠️ K8s-specific Grafana configs
│   ├── pipelines/
│   ├── scripts/
│   └── traefik/
└── monitoring/               # Application monitoring configs
    ├── grafana/
    │   ├── dashboards/
    │   └── provisioning/
    └── prometheus/
```

### Analysis

| Location | Purpose | Files Included |
|----------|---------|----------------|
| `/monitoring/` | Docker Compose observability stack | Grafana dashboards, Prometheus config |
| `/infrastructure/k8s/grafana/` | Kubernetes Grafana deployment | Helm values, K8s manifests |

### Recommendation: ✅ MOVE Monitoring to Infrastructure

**Proposed Structure:**
```
infrastructure/
├── monitoring/              # Move here
│   ├── docker/             # Docker Compose configs (current monitoring/)
│   │   ├── grafana/
│   │   └── prometheus/
│   └── k8s/                # Kubernetes configs (from infrastructure/k8s/grafana/)
│       └── grafana/
├── k8s/                    # Remove grafana from here
├── pipelines/
└── terraform/
```

**Benefits:**
- Consolidates all monitoring infrastructure in one place
- Clear separation between Docker and K8s configs
- Follows infrastructure-as-code best practices
- Reduces top-level folder clutter

---

## 3. Shared vs Libs Analysis

### Current Structure

| Folder | Purpose | Packages |
|--------|---------|----------|
| `shared/` | Core enterprise library | Single monolithic package with auth, config, db, observability, etc. |
| `libs/` | Specialized standalone packages | Currently only `settings/` |

### Content Comparison

**`shared/src/shared/` (Core Library):**
```
├── application/     # Application layer patterns
├── auth/           # JWT, passwords, API keys
├── cache/          # Caching utilities
├── config/         # BaseServiceSettings, domain settings
├── constants/      # HTTP status, environments
├── dbs/            # Repository, UoW patterns
├── ddd/            # DDD building blocks
├── exceptions/     # Custom exception hierarchy
├── extensions/     # Framework extensions
├── fastapi_utils/  # FastAPI helpers
├── http_client/    # HTTP client utilities
├── observability/  # Logging, tracing, metrics
├── proto/          # Protocol Buffers
├── sqlalchemy_async/  # Async SQLAlchemy
└── utils/          # General utilities
```

**`libs/settings/src/settings/` (Standalone Package):**
```
├── app_options.py
├── auth_options.py
├── caching_options.py
├── database_options.py
├── localization_options.py
├── logging_options.py
├── security_options.py
├── settings_manager.py
└── validators.py
```

### Problem: Overlap & Confusion

1. **Duplicate Concerns:** Both `shared/config/` and `libs/settings/` handle configuration
2. **Unclear Boundaries:** When to use `shared` vs `libs`?
3. **DDD Violation:** Settings are duplicated rather than following Single Responsibility

### Recommended Structure (DDD Best Practice)

```
packages/                    # Rename from libs/ for clarity
├── shared-kernel/          # DDD Shared Kernel (cross-cutting concerns)
│   └── src/shared/
│       ├── constants/
│       ├── exceptions/
│       ├── utils/
│       └── types/
├── infrastructure/         # Infrastructure layer packages
│   ├── observability/
│   ├── persistence/
│   └── messaging/
├── auth/                   # Auth bounded context
│   └── src/auth/
│       ├── jwt/
│       ├── password/
│       └── api_key/
└── config/                 # Configuration package (merge settings here)
    └── src/config/
        ├── base.py
        ├── database.py
        ├── cache.py
        └── auth.py
```

### Pragmatic Short-Term Fix

Keep current structure but:
1. **Deprecate `libs/settings/`** - merge into `shared/config/`
2. **Document clear purpose** in READMEs:
   - `shared/` = Enterprise library (always installed)
   - `libs/` = Optional specialized packages (future expansion)

---

## 4. GitHub Workflows Analysis

### Current Workflows

| Workflow | Status | Issues |
|----------|--------|--------|
| `python-ci.yml` | ⚠️ Partial | Missing `identity-service`, no libs coverage |
| `python-app.yml` | ❌ Outdated | Simple demo workflow, not used |
| `frontend-ci.yml` | ✅ Good | WebShell service coverage |
| `security-scan.yml` | ✅ Good | CodeQL + pip-audit |
| `release.yml` | ✅ Good | Semantic release |

### Issues to Fix

#### 1. `python-app.yml` - Remove or Update
```yaml
# Current: Simple demo that runs on every push
name: Python package
on: [push]  # ❌ Triggers on ALL pushes
```
**Action:** Delete this file (redundant with python-ci.yml)

#### 2. `python-ci.yml` - Missing Services
```yaml
# Missing in matrix:
- identity-service
- libs/settings
```

#### 3. Proposed Workflow Improvements

**Recommended Changes:**
```yaml
# python-ci.yml changes needed:

# 1. Add identity-service to path filters
paths:
  - 'services/identity-service/**'  # ADD

# 2. Add to detect-changes filters
identity-service:
  - 'services/identity-service/**'

# 3. Add to service matrix
- name: identity-service
  path: services/identity-service
```

---

## 5. Research Implementation Status

See updated [20250626-python-microservice-architecture-research.md](../research/20250626-python-microservice-architecture-research.md)

### Summary

| Research Item | Status | Notes |
|--------------|--------|-------|
| JWT RS256 token generation | ✅ Implemented | `shared/auth/jwt.py`, identity-service RSA keys |
| Password hashing (Argon2) | ✅ Implemented | `shared/auth/password.py` with PasswordService |
| Annotated type dependencies | ✅ Implemented | `identity_service/api/dependencies.py` |
| OAuth2 token endpoint | ✅ Implemented | PKCE, authorization_code, client_credentials |
| Async test setup | ✅ Implemented | pytest-asyncio, httpx AsyncClient |
| Structured logging | ✅ Implemented | structlog in all services |
| Settings with cache clear | ✅ Implemented | `get_settings.cache_clear()` |
| PKCE OAuth2 flow | ✅ Implemented | code_verifier in token endpoint |

### Remaining Tasks

| Task | Priority | Status |
|------|----------|--------|
| Add identity-service to CI pipeline | High | 🔴 Not Started |
| Remove python-app.yml workflow | Medium | 🔴 Not Started |
| Merge libs/settings into shared | Medium | 🔴 Not Started |
| Move monitoring to infrastructure | Low | 🔴 Not Started |
| Add user registration endpoints | Medium | 🟡 Partial |
| Add refresh_token grant flow | Medium | 🟡 Partial |
| 90%+ test coverage on auth flows | Medium | 🟡 Partial |

---

## Action Items

### Immediate (This Sprint)
1. [ ] Remove `python-app.yml` workflow
2. [ ] Add `identity-service` to `python-ci.yml`
3. [ ] Document shared vs libs purpose in READMEs

### Short-Term (Next Sprint)
4. [ ] Merge `libs/settings` into `shared/config`
5. [ ] Move `monitoring/` into `infrastructure/`
6. [ ] Complete test coverage for auth flows

### Long-Term (Roadmap)
7. [ ] Consider DDD package restructure
8. [ ] Add E2E testing workflow
9. [ ] Add performance testing (k6) to CI/CD
