"""Base abstractions for the background task framework.

Provides Task, PeriodicTask, and supporting types for defining
background work units with structured context and results.
"""

from __future__ import annotations

import enum
from abc import ABC
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class TaskStatus(str, enum.Enum):
    """Status of a task execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, enum.Enum):
    """Priority levels for task scheduling."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class TaskContext:
    """Execution context passed to every task.

    Attributes:
        task_id: Unique execution identifier.
        task_name: Human-readable task name.
        correlation_id: Distributed trace correlation ID.
        attempt: Current attempt number (1-based).
        max_attempts: Maximum retry attempts.
        metadata: Arbitrary key-value metadata.
        started_at: When the current attempt started.
    """

    task_id: str = field(default_factory=lambda: str(uuid4()))
    task_name: str = ""
    correlation_id: str | None = None
    attempt: int = 1
    max_attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TaskResult:
    """Result of a task execution.

    Attributes:
        task_id: Identifier of the executed task.
        status: Final execution status.
        result: Return value on success.
        error: Exception message on failure.
        started_at: When execution started.
        completed_at: When execution finished.
        attempts: Total attempts made.
        duration_ms: Wall-clock duration in milliseconds.
    """

    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 1
    duration_ms: float = 0.0


@dataclass
class TaskState:
    """Runtime state of a registered task.

    Attributes:
        name: Task name.
        status: Current status.
        last_run: When the task last ran.
        last_result: Result from the most recent run.
        run_count: Total number of executions.
        error_count: Total number of failed executions.
    """

    name: str
    status: TaskStatus = TaskStatus.PENDING
    last_run: datetime | None = None
    last_result: TaskResult | None = None
    run_count: int = 0
    error_count: int = 0


class TaskMiddleware(ABC):
    """Middleware hook that wraps every task execution.

    Implement ``before`` / ``after`` to add cross-cutting concerns
    such as logging, metrics, or distributed tracing.

    Example:
        >>> class MetricsMiddleware(TaskMiddleware):
        ...     async def before(self, ctx: TaskContext) -> None:
        ...         ctx.metadata["start_ns"] = time.perf_counter_ns()
        ...
        ...     async def after(self, ctx: TaskContext, result: TaskResult) -> None:
        ...         elapsed = time.perf_counter_ns() - ctx.metadata["start_ns"]
        ...         metrics.observe("task_duration_ns", elapsed, name=ctx.task_name)
    """

    async def before(self, ctx: TaskContext) -> None:  # noqa: B027
        """Called before task execution."""

    async def after(self, ctx: TaskContext, result: TaskResult) -> None:  # noqa: B027
        """Called after task execution (success or failure)."""


# Type alias for async task functions
TaskFn = Callable[..., Coroutine[Any, Any, Any]]


class Task:
    """A one-shot background task with optional retry.

    Wraps an async callable and adds retry semantics,
    timeout, and structured result tracking.

    Attributes:
        name: Human-readable task name.
        fn: The async callable to execute.
        max_attempts: Maximum execution attempts.
        retry_delay: Seconds between retries.
        timeout: Per-attempt timeout in seconds (``None`` = no limit).
        priority: Scheduling priority.

    Example:
        >>> async def send_email(to: str, body: str) -> None:
        ...     await smtp.send(to, body)
        >>>
        >>> task = Task(name="send-email", fn=send_email, max_attempts=3)
    """

    def __init__(
        self,
        *,
        name: str,
        fn: TaskFn,
        max_attempts: int = 1,
        retry_delay: float = 1.0,
        timeout: float | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> None:
        self.name = name
        self.fn = fn
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.priority = priority
        self.state = TaskState(name=name)


class PeriodicTask(Task):
    """A recurring background task.

    Extends :class:`Task` with an interval for repeated execution.

    Attributes:
        interval_seconds: Seconds between successive runs.
        run_immediately: Whether to fire once at startup.
        jitter_seconds: Random jitter added to interval to avoid thundering herd.

    Example:
        >>> @runner.periodic(interval_seconds=300)
        ... async def purge_stale_sessions():
        ...     await session_store.purge(older_than_minutes=30)
    """

    def __init__(
        self,
        *,
        name: str,
        fn: TaskFn,
        interval_seconds: float,
        run_immediately: bool = False,
        jitter_seconds: float = 0.0,
        max_attempts: int = 1,
        retry_delay: float = 1.0,
        timeout: float | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> None:
        super().__init__(
            name=name,
            fn=fn,
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            timeout=timeout,
            priority=priority,
        )
        self.interval_seconds = interval_seconds
        self.run_immediately = run_immediately
        self.jitter_seconds = jitter_seconds
