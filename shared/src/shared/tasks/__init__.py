"""Background task framework for microservices.

Provides abstractions for running background tasks, periodic/scheduled
tasks, and task lifecycle management with observability integration.

This module supports:
- **One-shot tasks**: Run-once async tasks with retry and timeout
- **Periodic tasks**: Cron-like scheduled tasks with configurable intervals
- **Task runner**: Manages task lifecycle (start, stop, health checks)
- **Task middleware**: Hooks for logging, metrics, error handling

Example:
    >>> from shared.tasks import TaskRunner, periodic, task
    >>>
    >>> runner = TaskRunner(name="my-service")
    >>>
    >>> @runner.periodic(interval_seconds=60)
    ... async def cleanup_expired_tokens():
    ...     await token_repo.delete_expired()
    >>>
    >>> @runner.task(name="send-welcome-email")
    ... async def send_welcome_email(user_id: str):
    ...     await email_service.send(user_id, "welcome")
"""

from __future__ import annotations

from shared.tasks.base import (
    PeriodicTask,
    Task,
    TaskContext,
    TaskMiddleware,
    TaskPriority,
    TaskResult,
    TaskState,
    TaskStatus,
)
from shared.tasks.runner import TaskRunner

__all__ = [
    # Core
    "Task",
    "PeriodicTask",
    "TaskRunner",
    # Data
    "TaskContext",
    "TaskResult",
    "TaskStatus",
    "TaskState",
    "TaskPriority",
    # Middleware
    "TaskMiddleware",
]
