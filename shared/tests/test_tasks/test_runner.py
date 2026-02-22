"""Tests for shared.tasks — background task framework."""

from __future__ import annotations

import asyncio

import pytest

from shared.tasks import (
    PeriodicTask,
    Task,
    TaskContext,
    TaskMiddleware,
    TaskPriority,
    TaskResult,
    TaskRunner,
    TaskState,
    TaskStatus,
)

# ── Fixtures ───────────────────────────────────────────────────────


class _CounterMiddleware(TaskMiddleware):
    """Test middleware that counts before/after calls."""

    def __init__(self) -> None:
        self.before_count = 0
        self.after_count = 0
        self.last_result: TaskResult | None = None

    async def before(self, ctx: TaskContext) -> None:
        self.before_count += 1

    async def after(self, ctx: TaskContext, result: TaskResult) -> None:
        self.after_count += 1
        self.last_result = result


# ── Unit Tests ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestTaskDataClasses:
    def test_task_context_defaults(self):
        ctx = TaskContext()
        assert ctx.attempt == 1
        assert ctx.max_attempts == 1
        assert ctx.task_name == ""
        assert ctx.task_id  # generated UUID

    def test_task_result_status(self):
        r = TaskResult(task_id="t1", status=TaskStatus.COMPLETED, result=42)
        assert r.status == TaskStatus.COMPLETED
        assert r.result == 42

    def test_task_state_defaults(self):
        s = TaskState(name="x")
        assert s.run_count == 0
        assert s.error_count == 0

    def test_task_priority_ordering(self):
        assert TaskPriority.LOW < TaskPriority.NORMAL < TaskPriority.HIGH < TaskPriority.CRITICAL


@pytest.mark.unit
class TestTask:
    def test_task_creation(self):
        async def dummy():
            pass

        t = Task(name="dummy", fn=dummy, max_attempts=3, timeout=5.0)
        assert t.name == "dummy"
        assert t.max_attempts == 3
        assert t.timeout == 5.0
        assert t.state.status == TaskStatus.PENDING

    def test_periodic_task_creation(self):
        async def dummy():
            pass

        pt = PeriodicTask(
            name="heartbeat",
            fn=dummy,
            interval_seconds=10,
            run_immediately=True,
            jitter_seconds=2.0,
        )
        assert pt.interval_seconds == 10
        assert pt.run_immediately is True
        assert pt.jitter_seconds == 2.0


@pytest.mark.unit
class TestTaskRunner:
    async def test_register_and_enqueue(self):
        runner = TaskRunner(name="test")
        call_log: list[str] = []

        @runner.task(name="greet", max_attempts=1)
        async def greet(name: str):
            call_log.append(name)
            return f"Hello, {name}"

        result = await runner.enqueue("greet", name="Alice")
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "Hello, Alice"
        assert call_log == ["Alice"]

    async def test_task_retry_on_failure(self):
        runner = TaskRunner(name="test")
        attempt_count = 0

        async def flaky():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("not yet")
            return "ok"

        runner.register(Task(name="flaky", fn=flaky, max_attempts=3, retry_delay=0.01))
        result = await runner.enqueue("flaky")
        assert result.status == TaskStatus.COMPLETED
        assert attempt_count == 3

    async def test_task_fails_after_max_attempts(self):
        runner = TaskRunner(name="test")

        async def always_fail():
            raise RuntimeError("boom")

        runner.register(Task(name="fail", fn=always_fail, max_attempts=2, retry_delay=0.01))
        result = await runner.enqueue("fail")
        assert result.status == TaskStatus.FAILED
        assert result.attempts == 2
        assert "boom" in (result.error or "")

    async def test_task_timeout(self):
        runner = TaskRunner(name="test")

        async def slow():
            await asyncio.sleep(10)

        runner.register(Task(name="slow", fn=slow, timeout=0.05))
        result = await runner.enqueue("slow")
        assert result.status == TaskStatus.FAILED

    async def test_unknown_task_raises_key_error(self):
        runner = TaskRunner(name="test")
        with pytest.raises(KeyError):
            await runner.enqueue("nonexistent")

    async def test_middleware_hooks(self):
        runner = TaskRunner(name="test")
        mw = _CounterMiddleware()
        runner.add_middleware(mw)

        async def noop():
            return 1

        runner.register(Task(name="noop", fn=noop))
        await runner.enqueue("noop")

        assert mw.before_count == 1
        assert mw.after_count == 1
        assert mw.last_result is not None
        assert mw.last_result.status == TaskStatus.COMPLETED

    async def test_get_states(self):
        runner = TaskRunner(name="test")

        async def noop():
            pass

        runner.register(Task(name="a", fn=noop))
        runner.register(Task(name="b", fn=noop))

        states = runner.get_states()
        assert "a" in states
        assert "b" in states
        assert states["a"].status == TaskStatus.PENDING

    async def test_is_healthy(self):
        runner = TaskRunner(name="test")

        async def fail():
            raise RuntimeError("fail")

        runner.register(Task(name="f", fn=fail))
        assert runner.is_healthy() is True

        await runner.enqueue("f")
        assert runner.is_healthy() is False


@pytest.mark.unit
class TestTaskRunnerLifecycle:
    async def test_periodic_task_runs(self):
        runner = TaskRunner(name="test")
        counter = {"n": 0}

        @runner.periodic(interval_seconds=0.05, run_immediately=True)
        async def tick():
            counter["n"] += 1

        async with runner:
            await asyncio.sleep(0.2)

        # Should have run multiple times
        assert counter["n"] >= 2

    async def test_start_stop(self):
        runner = TaskRunner(name="test")

        async def noop():
            pass

        runner.register(PeriodicTask(name="x", fn=noop, interval_seconds=0.1))

        await runner.start()
        assert runner._running is True
        await runner.stop()
        assert runner._running is False
        assert runner._background_tasks == []

    async def test_decorator_wrapper_calls_enqueue(self):
        runner = TaskRunner(name="test")

        @runner.task(name="add", max_attempts=1)
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(a=2, b=3)
        assert result.status == TaskStatus.COMPLETED
        assert result.result == 5
