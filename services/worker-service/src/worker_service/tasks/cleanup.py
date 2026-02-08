"""Cleanup task — removes expired sessions and stale data."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


async def cleanup_expired_sessions(ctx: dict[str, Any]) -> int:
    """Remove expired sessions and stale temporary data.

    Args:
        ctx: ARQ context dict.

    Returns:
        Number of records cleaned up.
    """
    # TODO: Wire up DB session and perform cleanup queries
    logger.info("cleanup_started")
    cleaned = 0
    logger.info("cleanup_completed", cleaned=cleaned)
    return cleaned
