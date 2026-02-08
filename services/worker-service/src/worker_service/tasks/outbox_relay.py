"""Outbox relay task — polls the outbox table and publishes pending events."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


async def process_outbox(ctx: dict[str, Any]) -> int:
    """Poll the transactional outbox and publish pending events.

    This task is the async complement of the OutboxRelay in the shared
    messaging module. It fetches unpublished outbox entries, publishes
    them to the message broker, and marks them as published.

    Args:
        ctx: ARQ context dict (contains settings, connections, etc.).

    Returns:
        Number of events published.
    """
    # TODO: Wire up OutboxRelay with real DB session + publisher
    logger.info("outbox_relay_started")
    published = 0
    logger.info("outbox_relay_completed", published=published)
    return published
