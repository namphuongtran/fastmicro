"""ARQ worker entry point and task definitions.

This module configures the ARQ worker and registers all background tasks.

Run with:
    arq worker_service.worker.WorkerSettings
"""

from __future__ import annotations

from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from worker_service.configs.settings import get_settings
from worker_service.tasks.outbox_relay import process_outbox
from worker_service.tasks.cleanup import cleanup_expired_sessions

logger = structlog.get_logger()


async def startup(ctx: dict[str, Any]) -> None:
    """ARQ worker startup hook."""
    settings = get_settings()
    logger.info(
        "Worker starting",
        service_name=settings.service_name,
        max_jobs=settings.arq_max_jobs,
    )
    ctx["settings"] = settings


async def shutdown(ctx: dict[str, Any]) -> None:
    """ARQ worker shutdown hook."""
    logger.info("Worker shutting down")


class WorkerSettings:
    """ARQ worker configuration.

    ARQ uses this class to discover tasks, cron jobs, and Redis settings.
    """

    functions = [process_outbox, cleanup_expired_sessions]
    cron_jobs = [
        cron(process_outbox, minute={0, 15, 30, 45}),  # every 15 min
        cron(cleanup_expired_sessions, hour={3}, minute={0}),  # daily 3 AM
    ]
    on_startup = startup
    on_shutdown = shutdown

    # ARQ expects redis_settings as a RedisSettings instance, not a callable
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

    max_jobs = get_settings().arq_max_jobs
    job_timeout = get_settings().arq_job_timeout_seconds
    keep_result = get_settings().arq_keep_result_seconds
    retry_jobs = get_settings().arq_retry_jobs
    max_tries = get_settings().arq_max_tries
