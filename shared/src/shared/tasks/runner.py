"""Task runner — manages lifecycle of background and periodic tasks.

The :class:`TaskRunner` is designed to integrate with FastAPI lifespan
or any ``async with`` context.  It starts all registered periodic tasks,
provides an ``enqueue`` method for one-shot tasks, and shuts down
gracefully on context exit.

Example:
    >>> runner = TaskRunner(name="audit-service")
    >>>
    >>> @runner.periodic(interval_seconds=60)
    ... async def flush_buffer():
    ...     await buffer.flush()
    >>>
    >>> async with runner:
    ...     # runner is active — periodic tasks are ticking
    ...     await runner.enqueue("send-email", to="a@b.com")
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from shared.tasks.base import (
    PeriodicTask,
    Task,
    TaskContext,
    TaskFn,
    TaskMiddleware,
    TaskPriority,
    TaskResult,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class TaskRunner:
    """Manages background and periodic task lifecycle.

    Attributes:
        name: Runner name (used in logs).
        tasks: Registry of all named tasks.
        middlewares: List of middleware hooks.

    Example:
        >>> runner = TaskRunner(name="my-service")
        >>> @runner.task(name="process-order", max_attempts=3)
        ... async def process_order(order_id: str) -> None: ...
        >>>
        >>> @runner.periodic(interval_seconds=120)
        ... async def heartbeat() -> None: ...
        >>>
        >>> async with runner:
        ...     result = await runner.enqueue("process-order", order_id="abc")
    """

    def __init__(self, *, name: str = "task-runner") -> None:
        self.name = name
        self.tasks: dict[str, Task] = {}
        self.middlewares: list[TaskMiddleware] = []
        self._background_tasks: list[asyncio.Task[None]] = []
        self._running = False

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def add_middleware(self, middleware: TaskMiddleware) -> None:
        """Register a task middleware."""
        self.middlewares.append(middleware)

    def register(self, task: Task) -> None:
        """Register a pre-built :class:`Task`."""
        self.tasks[task.name] = task

    def task(
        self,
        *,
        name: str,
        max_attempts: int = 1,
        retry_delay: float = 1.0,
        timeout: float | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Callable[[TaskFn], TaskFn]:
        """Decorator to register a one-shot task.

        Args:
            name: Unique task name.
            max_attempts: Retry attempts on failure.
            retry_delay: Seconds between retries.
            timeout: Per-attempt timeout.
            priority: Scheduling priority.

        Returns:
            Decorator that registers the function.
        """

        def decorator(fn: TaskFn) -> TaskFn:
            t = Task(
                name=name,
                fn=fn,
                max_attempts=max_attempts,
                retry_delay=retry_delay,
                timeout=timeout,
                priority=priority,
            )
            self.register(t)

            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.enqueue(name, *args, **kwargs)

            return wrapper  # type: ignore[return-value]

        return decorator

    def periodic(
        self,
        *,
        interval_seconds: float,
        name: str | None = None,
        run_immediately: bool = False,
        jitter_seconds: float = 0.0,
        max_attempts: int = 1,
        retry_delay: float = 1.0,
        timeout: float | None = None,
    ) -> Callable[[TaskFn], TaskFn]:
        """Decorator to register a periodic task.

        Args:
            interval_seconds: Seconds between runs.
            name: Task name (defaults to function name).
            run_immediately: Fire once at startup before entering loop.
            jitter_seconds: Random jitter added to interval.
            max_attempts: Retry attempts per run.
            retry_delay: Seconds between retries.
            timeout: Per-attempt timeout.

        Returns:
            Decorator that registers the function.
        """

        def decorator(fn: TaskFn) -> TaskFn:
            task_name = name or fn.__name__
            pt = PeriodicTask(
                name=task_name,
                fn=fn,
                interval_seconds=interval_seconds,
                run_immediately=run_immediately,
                jitter_seconds=jitter_seconds,
                max_attempts=max_attempts,
                retry_delay=retry_delay,
                timeout=timeout,
            )
            self.register(pt)
            return fn

        return decorator

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> TaskResult:
        """Execute a registered one-shot task.

        Args:
            task_name: Name of the registered task.
            *args: Positional arguments forwarded to the task function.
            **kwargs: Keyword arguments forwarded to the task function.

        Returns:
            :class:`TaskResult` with execution outcome.

        Raises:
            KeyError: If ``task_name`` is not registered.
        """
        task = self.tasks[task_name]
        return await self._execute_task(task, *args, **kwargs)

    async def _execute_task(self, task: Task, *args: Any, **kwargs: Any) -> TaskResult:
        """Execute a task with retry, timeout, and middleware."""
        ctx = TaskContext(
            task_name=task.name,
            max_attempts=task.max_attempts,
        )
        task.state.status = TaskStatus.RUNNING
        result = TaskResult(task_id=ctx.task_id, status=TaskStatus.RUNNING, started_at=ctx.started_at)

        for attempt in range(1, task.max_attempts + 1):
            ctx.attempt = attempt
            ctx.started_at = datetime.now(UTC)

            # Middleware — before
            for mw in self.middlewares:
                try:
                    await mw.before(ctx)
                except Exception:
                    logger.exception("Middleware before() failed for %s", task.name)

            try:
                if task.timeout:
                    value = await asyncio.wait_for(task.fn(*args, **kwargs), timeout=task.timeout)
                else:
                    value = await task.fn(*args, **kwargs)

                result.status = TaskStatus.COMPLETED
                result.result = value
                result.attempts = attempt
                break

            except asyncio.CancelledError:
                result.status = TaskStatus.CANCELLED
                result.error = "Task cancelled"
                break

            except Exception as exc:
                logger.warning(
                    "Task %s attempt %d/%d failed: %s",
                    task.name,
                    attempt,
                    task.max_attempts,
                    exc,
                )
                result.error = str(exc)
                result.attempts = attempt

                if attempt < task.max_attempts:
                    task.state.status = TaskStatus.RETRYING
                    result.status = TaskStatus.RETRYING
                    await asyncio.sleep(task.retry_delay)
                else:
                    result.status = TaskStatus.FAILED

            finally:
                result.completed_at = datetime.now(UTC)
                if result.started_at and result.completed_at:
                    delta = result.completed_at - ctx.started_at
                    result.duration_ms = delta.total_seconds() * 1000

                # Middleware — after
                for mw in self.middlewares:
                    try:
                        await mw.after(ctx, result)
                    except Exception:
                        logger.exception("Middleware after() failed for %s", task.name)

        # Update state
        task.state.status = result.status
        task.state.last_run = result.completed_at
        task.state.last_result = result
        task.state.run_count += 1
        if result.status == TaskStatus.FAILED:
            task.state.error_count += 1

        return result

    # ------------------------------------------------------------------
    # Periodic scheduling
    # ------------------------------------------------------------------

    async def _run_periodic(self, task: PeriodicTask) -> None:
        """Internal loop for a single periodic task."""
        if task.run_immediately:
            await self._execute_task(task)

        while self._running:
            jitter = random.uniform(0, task.jitter_seconds) if task.jitter_seconds else 0.0
            try:
                await asyncio.sleep(task.interval_seconds + jitter)
            except asyncio.CancelledError:
                break
            if not self._running:
                break
            await self._execute_task(task)

    # ------------------------------------------------------------------
    # Lifecycle (async context manager)
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start all periodic tasks."""
        if self._running:
            return
        self._running = True
        for task in self.tasks.values():
            if isinstance(task, PeriodicTask):
                bg = asyncio.create_task(
                    self._run_periodic(task),
                    name=f"periodic:{task.name}",
                )
                self._background_tasks.append(bg)
        logger.info("TaskRunner '%s' started with %d tasks", self.name, len(self.tasks))

    async def stop(self) -> None:
        """Gracefully stop all running tasks."""
        self._running = False
        for bg in self._background_tasks:
            bg.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        logger.info("TaskRunner '%s' stopped", self.name)

    async def __aenter__(self) -> TaskRunner:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_states(self) -> dict[str, TaskState]:
        """Return a snapshot of all task states (useful for health endpoints)."""
        return {name: task.state for name, task in self.tasks.items()}

    def is_healthy(self) -> bool:
        """Return ``True`` if no task is stuck in FAILED state."""
        return all(t.state.status != TaskStatus.FAILED for t in self.tasks.values())
