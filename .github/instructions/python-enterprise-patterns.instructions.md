---
description: 'Enterprise Python patterns and best practices for microservices including Repository, Unit of Work, Dependency Injection, and async patterns'
applyTo: '**/*.py'
---

# Python Enterprise Patterns

Guidelines for implementing enterprise-grade patterns in Python microservices for the fastmicro project.

## Core Architecture Principles

### Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│           API/Presentation              │  ← FastAPI routes, DTOs
├─────────────────────────────────────────┤
│           Application Layer             │  ← Use cases, services
├─────────────────────────────────────────┤
│           Domain Layer                  │  ← Entities, business logic
├─────────────────────────────────────────┤
│          Infrastructure Layer           │  ← Repositories, external APIs
└─────────────────────────────────────────┘
```

### Dependencies Flow Inward

- Outer layers depend on inner layers
- Inner layers define interfaces (protocols)
- Outer layers implement interfaces

## Repository Pattern

### Base Repository Interface

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Sequence
from pydantic import BaseModel

T = TypeVar("T")
ID = TypeVar("ID")

class IRepository(ABC, Generic[T, ID]):
    """Abstract repository interface."""
    
    @abstractmethod
    async def get(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        ...
    
    @abstractmethod
    async def get_all(self, *, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """Get all entities with pagination."""
        ...
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        ...
    
    @abstractmethod
    async def update(self, id: ID, entity: T) -> Optional[T]:
        """Update existing entity."""
        ...
    
    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        ...
    
    @abstractmethod
    async def exists(self, id: ID) -> bool:
        """Check if entity exists."""
        ...
```

### SQLAlchemy Implementation

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

class SQLAlchemyRepository(IRepository[T, ID], Generic[T, ID]):
    """Generic SQLAlchemy repository implementation."""
    
    def __init__(self, session: AsyncSession, model: type[DeclarativeBase]):
        self._session = session
        self._model = model
    
    async def get(self, id: ID) -> Optional[T]:
        result = await self._session.get(self._model, id)
        return result
    
    async def get_all(self, *, skip: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
    
    # ... other methods
```

## Unit of Work Pattern

### Interface

```python
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator

class IUnitOfWork(ABC):
    """Abstract Unit of Work interface."""
    
    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        ...
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        ...
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...
```

### Implementation

```python
class SQLAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy Unit of Work implementation."""
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None
    
    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()
    
    async def commit(self) -> None:
        await self._session.commit()
    
    async def rollback(self) -> None:
        await self._session.rollback()
    
    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork not started")
        return self._session
```

## Dependency Injection with FastAPI

### Annotated Dependencies

```python
from typing import Annotated
from fastapi import Depends

# Define reusable dependency types
SessionDep = Annotated[AsyncSession, Depends(get_session)]
UoWDep = Annotated[IUnitOfWork, Depends(get_unit_of_work)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

# Use in endpoints
@router.get("/items/{item_id}")
async def get_item(
    item_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ItemResponse:
    ...
```

### Factory Pattern for Dependencies

```python
def get_repository_factory(
    session: SessionDep,
) -> RepositoryFactory:
    """Factory for creating repositories with shared session."""
    return RepositoryFactory(session)

class RepositoryFactory:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    @property
    def users(self) -> UserRepository:
        return UserRepository(self._session)
    
    @property
    def items(self) -> ItemRepository:
        return ItemRepository(self._session)
```

## Exception Handling Patterns

### Custom Exception Hierarchy

```python
from typing import Optional, Dict, Any

class BaseAppException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }

class NotFoundError(BaseAppException):
    """Resource not found."""
    status_code = 404

class ValidationError(BaseAppException):
    """Validation failed."""
    status_code = 422

class AuthenticationError(BaseAppException):
    """Authentication failed."""
    status_code = 401

class AuthorizationError(BaseAppException):
    """Authorization failed."""
    status_code = 403
```

### Exception Handler Registration

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(
        request: Request, 
        exc: BaseAppException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
```

## Async Patterns

### Async Context Managers

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around operations."""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### Async Retry Pattern

```python
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator for async functions with retry logic."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator
```

## Service Layer Pattern

### Service Interface

```python
from abc import ABC, abstractmethod

class IUserService(ABC):
    """User service interface."""
    
    @abstractmethod
    async def get_user(self, user_id: int) -> UserResponse:
        ...
    
    @abstractmethod
    async def create_user(self, data: UserCreate) -> UserResponse:
        ...
    
    @abstractmethod
    async def update_user(self, user_id: int, data: UserUpdate) -> UserResponse:
        ...
```

### Service Implementation

```python
class UserService(IUserService):
    """User service implementation."""
    
    def __init__(
        self,
        uow: IUnitOfWork,
        password_hasher: IPasswordHasher,
        event_publisher: IEventPublisher,
    ):
        self._uow = uow
        self._password_hasher = password_hasher
        self._event_publisher = event_publisher
    
    async def create_user(self, data: UserCreate) -> UserResponse:
        async with self._uow:
            # Check for existing user
            if await self._uow.users.exists_by_email(data.email):
                raise ValidationError("Email already registered")
            
            # Create user
            user = User(
                email=data.email,
                hashed_password=self._password_hasher.hash(data.password),
            )
            user = await self._uow.users.create(user)
            await self._uow.commit()
            
            # Publish event
            await self._event_publisher.publish(
                UserCreatedEvent(user_id=user.id, email=user.email)
            )
            
            return UserResponse.model_validate(user)
```

## Configuration Pattern

### Settings with Pydantic

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Testing Patterns

### Repository Mocking

```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_user_repository() -> AsyncMock:
    repo = AsyncMock(spec=IUserRepository)
    repo.get.return_value = None
    repo.create.return_value = User(id=1, email="test@example.com")
    return repo
```

### Service Testing

```python
@pytest.mark.asyncio
async def test_create_user_success(
    mock_uow: AsyncMock,
    mock_password_hasher: AsyncMock,
    mock_event_publisher: AsyncMock,
):
    # Arrange
    service = UserService(mock_uow, mock_password_hasher, mock_event_publisher)
    data = UserCreate(email="test@example.com", password="password123")
    
    # Act
    result = await service.create_user(data)
    
    # Assert
    assert result.email == "test@example.com"
    mock_event_publisher.publish.assert_called_once()
```
