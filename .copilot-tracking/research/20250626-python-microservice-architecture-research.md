<!-- markdownlint-disable-file -->

# Task Research Notes: Python Microservice Architecture Patterns

## Research Executed

### File Analysis

- **shared/src/shared/config/base.py**
  - Thread-safe settings caching pattern with lock-based alternative to `@lru_cache`
  - `BaseServiceSettings` extends pydantic-settings `BaseSettings`
  - Environment property helpers (`is_development`, `is_production`, `is_staging`, `is_testing`)
  - `SettingsConfigDict` for `.env` file loading with `extra="ignore"`

- **services/identity-service/src/identity_service/main.py**
  - FastAPI lifespan context manager pattern with `@asynccontextmanager`
  - Structured logging with `structlog`
  - Environment-based conditional docs URL (None in production)
  - Factory function `create_app()` pattern for testability

- **shared/src/shared/config/__init__.py**
  - Clean public API exports with `__all__`
  - Domain-split settings: `DatabaseSettings`, `RedisSettings`, `AuthSettings`
  - `get_settings()` and `clear_settings_cache()` utility functions

### Code Search Results

- **BaseSettings patterns across services**
  - `metastore-service`: Uses `BaseServiceSettings` from shared
  - `identity-service`: Uses `BaseServiceSettings` with custom extensions
  - Pattern: Services import from `shared.config` and extend with service-specific fields

### External Research

- **#githubRepo:"fastapi/full-stack-fastapi-template"**
  - Annotated type dependencies: `CurrentUser = Annotated[User, Depends(get_current_active_user)]`
  - Router organization: Feature-based routers in `app/api/routes/`
  - SQLModel for database models with Pydantic integration
  - JWT implementation with `python-jose` (RS256 support)
  - Password hashing with `pwdlib[argon2,bcrypt]`

- **#githubRepo:"Netflix/dispatch"**
  - Plugin-based auth provider system
  - PKCE OAuth2 flow implementation
  - Starlette-based configuration management
  - Service-layer abstraction between routes and database

- **#githubRepo:"zhanymkanov/fastapi-best-practices"**
  - Comprehensive anti-pattern documentation
  - Async vs sync guidance for routes
  - BaseSettings caching patterns
  - Testing strategies with httpx AsyncClient

- **#fetch:https://fastapi.tiangolo.com/tutorial/bigger-applications/**
  - APIRouter for modular route organization
  - Tags, prefix, and dependencies at router level
  - Nested router includes with `include_router()`

- **#fetch:https://fastapi.tiangolo.com/advanced/settings/**
  - Pydantic Settings v2 with `SettingsConfigDict`
  - `@lru_cache` for settings singleton pattern
  - `Depends(get_settings)` for dependency injection

- **#fetch:https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/**
  - OAuth2PasswordBearer for token extraction
  - JWT encoding/decoding with python-jose
  - Password hashing with passlib (deprecated) → use pwdlib

- **#fetch:https://fastapi.tiangolo.com/async/**
  - Use `async def` for I/O-bound operations (database, HTTP calls)
  - Use regular `def` for CPU-bound operations (FastAPI runs in threadpool)
  - Never use blocking calls in `async def` routes

- **#fetch:https://docs.python.org/3/library/datetime.html**
  - `datetime.now(timezone.utc)` for timezone-aware UTC timestamps
  - `datetime.utcnow()` is deprecated - returns naive datetime
  - Always use aware datetimes in production code

### Project Conventions

- Standards referenced: `.github/instructions/python.instructions.md`, `python-enterprise-patterns.instructions.md`
- Instructions followed: `cloud-native-python.instructions.md`, `observability.instructions.md`

---

## Key Discoveries

### Project Structure Patterns

#### Pattern 1: Feature-Based Organization (FastAPI Full-Stack Template)

```
app/
├── api/
│   ├── deps.py           # Shared dependencies
│   ├── main.py           # FastAPI app creation
│   └── routes/
│       ├── items.py
│       ├── login.py
│       └── users.py
├── core/
│   ├── config.py         # Settings
│   ├── db.py             # Database session
│   └── security.py       # Auth utilities
├── crud/
│   ├── base.py           # Generic CRUD
│   └── crud_user.py
├── models/
│   └── user.py           # SQLModel models
└── schemas/
    └── user.py           # Pydantic schemas (if separate from models)
```

#### Pattern 2: Domain-Driven Organization (Netflix Dispatch)

```
src/
├── dispatch/
│   ├── auth/
│   │   ├── models.py
│   │   ├── service.py
│   │   └── views.py
│   ├── incident/
│   │   ├── models.py
│   │   ├── service.py
│   │   └── views.py
│   └── plugins/
│       └── dispatch_core/
│           └── auth/
│               └── basic.py
```

#### Current Project Pattern (fastmicro)

```
services/
└── identity-service/
    └── src/
        └── identity_service/
            ├── main.py           # App factory
            ├── api/              # Route handlers
            ├── core/             # Config, security
            ├── models/           # Database models
            └── services/         # Business logic
shared/
└── src/
    └── shared/
        ├── auth/                 # JWT, permissions
        ├── config/               # BaseSettings
        ├── dbs/                  # Database utilities
        ├── exceptions/           # Custom exceptions
        └── observability/        # Logging, tracing
```

### Implementation Patterns

#### Dependency Injection with Annotated Types (Recommended)

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Define reusable type aliases
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

# Use in route handlers - clean signatures
@router.get("/users/me")
async def read_users_me(current_user: CurrentUser) -> User:
    return current_user

@router.get("/items")
async def read_items(session: SessionDep, current_user: CurrentUser) -> list[Item]:
    return await crud.get_items(session, owner_id=current_user.id)
```

#### Chained Dependencies with Caching

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    """Cached settings - called once per process."""
    return Settings()

def get_db_session(settings: Annotated[Settings, Depends(get_settings)]) -> AsyncSession:
    """Database session depends on cached settings."""
    # Session creation logic
    pass

def get_current_user(
    token: TokenDep,
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> User:
    """Chain: settings -> session -> user validation."""
    pass
```

#### Settings Configuration (Pydantic Settings v2)

```python
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    """Database-specific settings."""
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    host: str = "localhost"
    port: int = 5432
    name: str = "app"
    user: str = "postgres"
    password: str = ""  # Load from environment
    
    @computed_field
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class Settings(BaseSettings):
    """Main application settings - composes domain settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    app_name: str = "MyService"
    environment: str = "development"
    debug: bool = False
    
    # Composed settings
    database: DatabaseSettings = DatabaseSettings()
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

### Complete Examples

#### JWT Authentication Implementation

```python
# core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Password hashing with Argon2 (recommended over bcrypt)
password_hash = PasswordHash([Argon2Hasher()])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

# JWT token creation
def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    private_key: str = settings.JWT_PRIVATE_KEY,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(to_encode, private_key, algorithm="RS256")

def decode_token(token: str, public_key: str = settings.JWT_PUBLIC_KEY) -> dict:
    try:
        return jwt.decode(token, public_key, algorithms=["RS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### Async Test Setup

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.deps import get_session
from app.models import Base

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Example test
@pytest.mark.anyio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "password": "secret123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

### API and Schema Documentation

#### OAuth2 Token Response Schema

```python
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration
    refresh_token: str | None = None
    scope: str | None = None

class TokenPayload(BaseModel):
    sub: str  # Subject (user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # Token type (access/refresh)
    scopes: list[str] = []
```

### Technical Requirements

- **Python**: 3.11+ (for improved typing and performance)
- **FastAPI**: 0.100+ (native Pydantic v2 support)
- **Pydantic Settings**: 2.0+ (separate package from pydantic)
- **SQLAlchemy**: 2.0+ (native async support)
- **pytest-asyncio**: 0.21+ (for async test fixtures)
- **httpx**: For async test client
- **pwdlib**: Password hashing (replaces passlib)
- **PyJWT**: JWT encoding/decoding (or python-jose)

---

## Common Anti-Patterns to Avoid

### 1. Blocking Calls in Async Routes

```python
# BAD: Blocking I/O in async route
@router.get("/users")
async def get_users():
    time.sleep(1)  # Blocks the event loop!
    users = requests.get("http://external-api/users")  # Blocking HTTP
    return users.json()

# GOOD: Use async libraries
@router.get("/users")
async def get_users():
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        response = await client.get("http://external-api/users")
    return response.json()

# ALTERNATIVE: Use sync def for CPU-bound or unavoidably blocking code
@router.get("/cpu-intensive")
def process_data():  # FastAPI runs this in threadpool
    result = heavy_computation()
    return {"result": result}
```

### 2. Naive Datetime Usage

```python
# BAD: Naive datetime (no timezone info)
from datetime import datetime
created_at = datetime.utcnow()  # Deprecated in Python 3.12

# GOOD: Timezone-aware datetime
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)

# For database models
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class User(Base):
    # BAD
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # GOOD
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 3. Settings Cache Without Clear Function

```python
# BAD: No way to clear cache in tests
from functools import lru_cache

@lru_cache
def get_settings():
    return Settings()

# Tests can't override settings!

# GOOD: Provide cache clear function
from functools import lru_cache

@lru_cache
def get_settings():
    return Settings()

def clear_settings_cache():
    get_settings.cache_clear()

# In tests:
def test_with_different_settings():
    clear_settings_cache()
    # Now new settings will be loaded
```

### 4. Mixing Async and Sync Database Operations

```python
# BAD: Sync operations in async context
@router.get("/items")
async def get_items(session: AsyncSession):
    # This blocks!
    items = session.query(Item).all()
    return items

# GOOD: Use async operations
@router.get("/items")
async def get_items(session: AsyncSession):
    result = await session.execute(select(Item))
    items = result.scalars().all()
    return items
```

### 5. Hardcoded Configuration

```python
# BAD: Hardcoded values
DATABASE_URL = "postgresql://user:pass@localhost/db"
JWT_SECRET = "my-secret-key"

# GOOD: Environment-based configuration
class Settings(BaseSettings):
    database_url: str  # Required from environment
    jwt_secret: str = Field(..., min_length=32)  # Validated
    
    model_config = SettingsConfigDict(env_file=".env")
```

### 6. Missing Error Handling in Dependencies

```python
# BAD: Unhandled exceptions leak internal details
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY)  # Can raise various exceptions
    user = await get_user(payload["sub"])
    return user

# GOOD: Proper exception handling
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["RS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await get_user(user_id)
    if user is None:
        raise credentials_exception
    return user
```

---

## Recommended Approach

Based on research findings, the recommended implementation approach for the identity service:

### Architecture

1. **Project Structure**: Domain-driven organization matching current `fastmicro` pattern
2. **Configuration**: Domain-split settings extending `BaseServiceSettings` from shared
3. **Dependencies**: Annotated type aliases for clean route signatures
4. **Authentication**: RS256 JWT with `PyJWT`, password hashing with `pwdlib[argon2]`
5. **Testing**: pytest-asyncio with httpx AsyncClient, dependency override pattern

### Key Implementation Decisions

| Aspect | Recommended Choice | Rationale |
|--------|-------------------|-----------|
| Password Hashing | pwdlib with Argon2 | Modern, maintained, winner of PHC |
| JWT Library | PyJWT | Simpler API than python-jose, RS256 support |
| Async Testing | httpx + ASGITransport | Native async support, no need for external server |
| Settings | Pydantic Settings v2 | Built-in validation, env file support |
| Database | SQLAlchemy 2.0 async | Native async, type hints, session management |

---

## Implementation Guidance

- **Objectives**: Build production-ready identity service with OAuth2/OIDC capabilities
- **Key Tasks**:
  1. Implement JWT RS256 token generation/validation using existing RSA key patterns
  2. Add password hashing with pwdlib Argon2
  3. Create user registration/login endpoints following FastAPI template patterns
  4. Add async test suite with httpx client
  5. Integrate with shared observability (structlog, OpenTelemetry)
- **Dependencies**: pwdlib[argon2], PyJWT, httpx (for tests)
- **Success Criteria**:
  - All auth endpoints return proper OAuth2 token responses
  - Password hashes use Argon2 with secure defaults
  - 90%+ test coverage on auth flows
  - Structured logging on all auth events

---

## Implementation Status (Updated: 2026-02-01)

### ✅ Completed Items

| Task | Location | Evidence |
|------|----------|----------|
| JWT RS256 token generation/validation | `shared/src/shared/auth/jwt.py` | JWTService class with HS256/RS256 support, TokenData, expiration handling |
| Password hashing (Argon2) | `shared/src/shared/auth/password.py` | PasswordService with argon2-cffi, configurable params |
| Password strength validation | `shared/src/shared/auth/password.py` | `check_password_strength()` function |
| API Key management | `shared/src/shared/auth/api_key.py` | APIKeyService with prefix support |
| Annotated type dependencies | `identity_service/api/dependencies.py` | OAuth2ServiceDep and other type aliases |
| OAuth2 token endpoint | `identity_service/api/oauth/token.py` | authorization_code, client_credentials, refresh_token grants |
| PKCE OAuth2 flow | `identity_service/api/oauth/token.py` | code_verifier parameter in token endpoint |
| OAuth2 authorization endpoint | `identity_service/api/oauth/authorize.py` | Authorization code flow with consent |
| OpenID Connect discovery | `identity_service/api/oauth/discovery.py` | `.well-known/openid-configuration` |
| Token introspection | `identity_service/api/oauth/introspection.py` | RFC 7662 compliant |
| UserInfo endpoint | `identity_service/api/oauth/userinfo.py` | OIDC userinfo |
| Async test setup | `identity_service/tests/conftest.py` | pytest-asyncio, httpx AsyncClient, ASGITransport |
| Structured logging | `identity_service/main.py` | structlog with LoggingConfig from shared |
| Request logging middleware | `identity_service/main.py` | RequestLoggingMiddleware from shared |
| Settings with cache clear | `identity_service/configs.py` | `get_settings.cache_clear()` in conftest.py |
| Domain entities (DDD) | `identity_service/domain/entities/` | User, Client, Token, Consent entities |
| Value objects | `identity_service/domain/value_objects.py` | ClientId, Email, Scope, GrantType, etc. |
| FastAPI lifespan pattern | `identity_service/main.py` | `@asynccontextmanager` lifespan handler |
| Factory function pattern | `identity_service/main.py` | `create_app()` for testability |
| Environment-based docs URL | `identity_service/main.py` | None in production |

### 🟡 Partially Implemented

| Task | Status | What's Missing |
|------|--------|----------------|
| User registration endpoints | 50% | Domain entities exist, need API endpoints `/users/register` |
| User login endpoints | 50% | OAuth flow exists, need direct `/users/login` endpoint |
| Refresh token grant | 80% | Grant type handler exists, need token storage/rotation |
| Test coverage (90%+) | 60% | Unit tests exist, need more integration tests |
| Database integration | 40% | Repositories defined, need actual DB session management |

### 🔴 Not Started

| Task | Priority | Notes |
|------|----------|-------|
| CI pipeline update (identity-service) | High | Add to python-ci.yml matrix |
| Remove python-app.yml | Medium | Outdated demo workflow |
| OpenTelemetry tracing integration | Medium | Shared library ready, need service integration |
| Prometheus metrics endpoints | Low | `/metrics` endpoint |
| Rate limiting on auth endpoints | Medium | Brute force protection |
| Account lockout mechanism | Medium | After N failed attempts |
| Password reset flow | Low | Email verification required |
| MFA/2FA support | Low | TOTP, WebAuthn |

### Next Steps (Priority Order)

1. **Immediate:** Add identity-service to CI pipeline
2. **This Sprint:** Complete user registration/login API endpoints
3. **This Sprint:** Add database session management with SQLAlchemy async
4. **Next Sprint:** Implement rate limiting and account lockout
5. **Next Sprint:** Achieve 90%+ test coverage
