---
description: 'Mandatory architectural design process, research requirements, and anti-patterns to avoid. Lessons learned from production debugging sessions.'
applyTo: '**/*.py'
---

# Architectural Design Process

Guidelines for designing features and modules with proper research, planning, and validation before implementation. This document captures critical lessons learned from production debugging sessions.

## Core Principle: Research → Design → Validate → Implement

**Never start coding without completing the research and design phases.**

```
┌─────────────────────────────────────────────────────────────────┐
│  1. RESEARCH                                                     │
│     • Search GitHub repos (>5k stars) for patterns              │
│     • Use Context7 MCP for library documentation                │
│     • Review existing shared/ library capabilities              │
├─────────────────────────────────────────────────────────────────┤
│  2. DESIGN                                                       │
│     • Use sequential-thinking MCP for complex problems          │
│     • Document decisions in ADR if architectural                │
│     • Validate against shared library patterns                  │
├─────────────────────────────────────────────────────────────────┤
│  3. VALIDATE                                                     │
│     • Run architecture agent for design review                  │
│     • Check for anti-patterns listed below                      │
│     • Verify shared library integration                         │
├─────────────────────────────────────────────────────────────────┤
│  4. IMPLEMENT                                                    │
│     • Follow established patterns from research                 │
│     • Use shared library utilities                              │
│     • Write tests alongside implementation                      │
├─────────────────────────────────────────────────────────────────┤
│  5. TEST                                                         │
│     • Unit tests with proper fixtures                           │
│     • Integration tests with cache clearing                     │
│     • No hardcoded paths or secrets                             │
└─────────────────────────────────────────────────────────────────┘
```

## Mandatory Tool Usage

### When to Use Sequential Thinking MCP

Use `mcp_sequential-th_sequentialthinking` for:

- Designing new modules or features
- Debugging complex multi-layer issues
- Making architectural decisions with trade-offs
- Planning multi-step refactoring
- Evaluating multiple implementation approaches

```markdown
# Example: Designing JWT Service
Thought 1: Define requirements (token types, algorithms, expiration)
Thought 2: Research existing patterns (authlib, PyJWT, python-jose)
Thought 3: Evaluate trade-offs (RS256 vs HS256, library complexity)
Thought 4: Check shared library for existing utilities
Thought 5: Design interface matching shared patterns
Thought 6: Plan test strategy
```

### When to Use GitHub Repository Search

Before implementing any significant feature:

1. Search for repos with >5k stars implementing similar patterns
2. Look for official examples from library maintainers
3. Check community-recommended approaches

**Key repositories to reference:**

| Pattern | Repository | Stars |
|---------|------------|-------|
| FastAPI Project Structure | `fastapi/full-stack-fastapi-template` | 30k+ |
| FastAPI Best Practices | `zhanymkanov/fastapi-best-practices` | 10k+ |
| Clean Architecture | `cosmicpython/book` | 3k+ |
| OAuth2/OIDC | `authlib/authlib` | 4k+ |

### When to Use Context7 MCP

Use `mcp_context7_get-library-docs` for:

- Understanding library APIs before implementation
- Checking for deprecated patterns
- Finding recommended usage examples

---

## Critical Anti-Patterns to Avoid

### 1. Datetime Timestamp Bug

**NEVER use `datetime.utcnow().timestamp()`**

```python
# ❌ WRONG - Creates incorrect timestamps
from datetime import datetime
exp = datetime.utcnow().timestamp()  # BUG: .timestamp() assumes LOCAL timezone

# ✅ CORRECT - Use time.time() for Unix timestamps
import time
exp = int(time.time())

# ✅ CORRECT - Use shared utility for datetime objects
from shared.utils import now_utc
now = now_utc()  # Returns timezone-aware UTC datetime
```

**Why this matters:** `datetime.utcnow()` returns a naive datetime (no timezone info). When you call `.timestamp()` on it, Python assumes it's in the LOCAL timezone and converts accordingly. This caused JWT tokens to be "expired" immediately because the `exp` claim was hours in the past.

### 2. @lru_cache with Unhashable Arguments

**NEVER use Pydantic models as `@lru_cache` arguments**

```python
# ❌ WRONG - Settings is unhashable
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str

@lru_cache
def get_service(settings: Settings):  # TypeError: unhashable type
    return MyService(settings)

# ✅ CORRECT - Use primitive arguments
@lru_cache
def get_service(api_key: str) -> MyService:
    return MyService(api_key)

# ✅ CORRECT - Manual cache with cache_clear support
_service_cache: dict[str, MyService] = {}

def get_service(settings: Settings) -> MyService:
    cache_key = f"{settings.api_key}"
    if cache_key not in _service_cache:
        _service_cache[cache_key] = MyService(settings)
    return _service_cache[cache_key]

def clear_service_cache() -> None:
    _service_cache.clear()
```

### 3. Hardcoded Paths

**NEVER hardcode container/production paths**

```python
# ❌ WRONG - Breaks local development and tests
private_key_path: str = "/app/keys/private.pem"

# ✅ CORRECT - Use environment variables with sensible defaults
import os
private_key_path: str = os.getenv(
    "JWT_PRIVATE_KEY_PATH", 
    str(Path.home() / ".config/myapp/keys/private.pem")
)

# ✅ CORRECT - Pydantic Settings with env vars
class Settings(BaseSettings):
    jwt_private_key_path: str = Field(
        default="keys/private.pem",
        description="Path to JWT private key"
    )
    
    model_config = SettingsConfigDict(env_file=".env")
```

### 4. Manual Service Instantiation in FastAPI

**ALWAYS use `Depends()` for service injection**

```python
# ❌ WRONG - Manual instantiation bypasses DI
@router.post("/token")
async def token_endpoint(request: Request):
    oauth2_service = await get_oauth2_service()  # No settings passed!
    return await oauth2_service.handle_token(request)

# ✅ CORRECT - Use FastAPI Depends
from typing import Annotated
from fastapi import Depends

@router.post("/token")
async def token_endpoint(
    request: Request,
    oauth2_service: Annotated[OAuth2Service, Depends(get_oauth2_service)]
):
    return await oauth2_service.handle_token(request)
```

### 5. Not Using Shared Library

**ALWAYS check shared/ before implementing utilities**

```python
# ❌ WRONG - Reimplementing what exists in shared
class InMemoryUserRepository:
    def __init__(self):
        self._users: dict[str, User] = {}
    # ... 100+ lines of custom implementation

# ✅ CORRECT - Use shared library
from shared.dbs import InMemoryRepository

class UserRepository(InMemoryRepository[User, str]):
    """User repository using shared base class."""
    pass
```

**Available in shared library:**

| Need | Import |
|------|--------|
| Repository pattern | `from shared.dbs import AbstractRepository, InMemoryRepository` |
| Unit of Work | `from shared.dbs import AbstractUnitOfWork, InMemoryUnitOfWork` |
| Exceptions | `from shared.exceptions import NotFoundError, ValidationException` |
| Datetime utilities | `from shared.utils import now_utc, format_iso8601` |
| DI Container | `from shared.extensions import Container, Depends, inject` |
| Logging | `from shared.observability import get_logger, configure_logging` |
| Retry/Circuit breaker | `from shared.extensions import retry, cache, timeout` |

### 6. Tests Without Cache Clearing

**ALWAYS clear caches in test fixtures**

```python
# ❌ WRONG - Stale cache causes test pollution
@pytest.fixture
def app():
    return create_app()

# ✅ CORRECT - Clear all caches before creating app
@pytest.fixture
def app(test_settings: Settings, monkeypatch):
    # Clear any cached services
    from myservice.dependencies import clear_service_cache
    clear_service_cache()
    
    # Also clear lru_cache if used
    from myservice.config import get_settings
    if hasattr(get_settings, 'cache_clear'):
        get_settings.cache_clear()
    
    # Set environment variables for test
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    return create_app(settings=test_settings)
```

### 7. Blocking Calls in Async Code

**NEVER use blocking I/O in async functions**

```python
# ❌ WRONG - Blocks the event loop
import requests

async def fetch_data():
    response = requests.get("https://api.example.com")  # BLOCKING!
    return response.json()

# ✅ CORRECT - Use async HTTP client
import httpx

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

---

## Pre-Implementation Checklist

Before writing any code, verify:

- [ ] **Researched** similar implementations in popular repos
- [ ] **Checked** shared/ library for existing utilities
- [ ] **Designed** using sequential-thinking for complex features
- [ ] **Documented** architectural decisions in ADR if significant
- [ ] **Validated** against anti-patterns listed above

## Pre-PR Checklist

Before creating a pull request, verify:

- [ ] All tests pass (`uv run pytest tests/ -v`)
- [ ] No hardcoded paths or secrets
- [ ] Uses FastAPI `Depends()` for all service injection
- [ ] Uses shared library utilities where applicable
- [ ] Test fixtures clear caches appropriately
- [ ] No `datetime.utcnow().timestamp()` usage
- [ ] No blocking I/O in async functions
- [ ] No `@lru_cache` with unhashable arguments

---

## Recommended Refactoring Tasks

Based on the debugging session analysis, the following technical debt should be addressed:

### identity-service

1. **Adopt shared library patterns**
   - Replace custom `InMemoryUserRepository` (300+ lines) with `shared.dbs.InMemoryRepository`
   - Use `shared.exceptions` instead of custom exceptions

2. **Fix deprecated datetime usage**
   - Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` or `shared.utils.now_utc()`
   - Files affected: `domain/entities/token.py`, `domain/entities/consent.py`

3. **Standardize configuration**
   - Add `dependency-injector` like metastore-service uses
   - Create proper DI container for services

### All Services

1. **Create datetime utility in shared**
   - Add `utc_timestamp()` function that returns `int(time.time())`
   - Add deprecation warnings for `utcnow()` usage in linting

2. **Document testing patterns**
   - Create shared test fixtures for cache clearing
   - Document temp directory patterns for key files

---

## Summary

The key lesson is: **Think before you code.** Use the tools available:

1. **Sequential Thinking** for design decisions
2. **GitHub Search** for proven patterns
3. **Context7** for library documentation
4. **Shared Library** for common utilities
5. **Architecture Agents** for validation

Reactive bug-fixing is expensive. Proactive design is an investment that pays dividends.

---

<!-- End of Architectural Design Process Instructions -->
