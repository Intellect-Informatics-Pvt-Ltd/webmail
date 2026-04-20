"""PSense Mail — Worker manager.

Starts and stops all background workers with graceful shutdown.
"""
from __future__ import annotations

import asyncio
import logging

from app.workers.inbound_poller import InboundPollerWorker
from app.workers.retry import RetryWorker
from app.workers.scheduler import ScheduledSendWorker
from app.workers.snooze import SnoozeWorker
from config.settings import Settings

logger = logging.getLogger(__name__)

# Graceful shutdown timeout (seconds)
_SHUTDOWN_TIMEOUT = 10


class WorkerManager:
    """Manages background task lifecycles."""

    def __init__(self, settings: Settings, adapter_registry):
        self.settings = settings
        self._workers = []

        # 1. Snooze worker
        self._workers.append(SnoozeWorker(interval=settings.workers.snooze_check_interval_seconds))

        # 2. Scheduled send worker
        self._workers.append(
            ScheduledSendWorker(
                transport=adapter_registry.transport,
                interval=getattr(settings.workers, "scheduler_interval_seconds", 30),
                default_from_address=settings.provider.mailpit.from_address,
            )
        )

        # 3. Retry worker
        self._workers.append(
            RetryWorker(
                transport=adapter_registry.transport,
                interval=60,
                max_attempts=settings.workers.send_retry_max_attempts,
                backoff_base_sec=getattr(settings.workers, "retry_backoff_base_seconds", 60),
                default_from_address=settings.provider.mailpit.from_address,
            )
        )

        # 4. Inbound poller (only for provider with polling support)
        self.inbound_poller: InboundPollerWorker | None = None
        if settings.provider.active in ("mailpit", "pop3"):
            inbound_adapter = adapter_registry.inbound
            self.inbound_poller = InboundPollerWorker(
                adapter=inbound_adapter,
                cache_user_id=settings.auth.dev_user_id,
                poll_interval=settings.workers.sync_interval_seconds,
            )
            self._workers.append(self.inbound_poller)

    def start_all(self) -> None:
        """Start all workers."""
        if not self.settings.workers.enabled:
            logger.info("Background workers are disabled in configuration")
            return

        logger.info("Starting %d background workers...", len(self._workers))
        for worker in self._workers:
            worker.start()

    async def stop_all_async(self) -> None:
        """Stop all workers with graceful shutdown and timeout."""
        logger.info("Stopping %d background workers (timeout=%ds)...", len(self._workers), _SHUTDOWN_TIMEOUT)

        # Signal all workers to stop
        for worker in self._workers:
            try:
                worker.stop()
            except Exception as e:
                logger.error("Failed to signal stop for worker %s: %s", worker.__class__.__name__, e)

        # Gather all worker tasks and wait with timeout
        tasks = [w._task for w in self._workers if hasattr(w, "_task") and w._task is not None]
        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=_SHUTDOWN_TIMEOUT)
            if pending:
                logger.warning("%d workers did not finish within timeout, cancelling...", len(pending))
                for task in pending:
                    task.cancel()
                # Wait for cancellation to complete
                await asyncio.gather(*pending, return_exceptions=True)

        logger.info("All background workers stopped")

    def stop_all(self) -> None:
        """Stop all workers (sync wrapper for backward compatibility)."""
        for worker in self._workers:
            try:
                worker.stop()
            except Exception as e:
                logger.error("Failed to stop worker %s: %s", worker.__class__.__name__, e)
