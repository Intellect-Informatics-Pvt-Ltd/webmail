"""PSense Mail — Worker manager.

Starts and stops all background workers.
"""
from __future__ import annotations

import logging

from app.workers.inbound_poller import InboundPollerWorker
from app.workers.snooze import SnoozeWorker
from config.settings import Settings

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages background task lifecycles."""

    def __init__(self, settings: Settings, adapter_registry):
        self.settings = settings
        self._workers = []
        
        # 1. Snooze worker
        self._workers.append(SnoozeWorker(interval=settings.workers.snooze_check_interval_seconds))
        
        # 2. Inbound poller
        if settings.provider.active == "mailpit":
            from app.adapters.inbound.mailpit import MailPitInboundAdapter
            
            inbound_adapter = MailPitInboundAdapter(
                api_url=settings.provider.mailpit.api_url
            )
            self._workers.append(
                InboundPollerWorker(
                    adapter=inbound_adapter,
                    cache_user_id=settings.auth.dev_user_id,
                    poll_interval=settings.workers.sync_interval_seconds,
                )
            )

    def start_all(self):
        """Start all workers."""
        if not self.settings.workers.enabled:
            logger.info("Background workers are disabled in configuration")
            return
            
        logger.info("Starting %d background workers...", len(self._workers))
        for worker in self._workers:
            worker.start()

    def stop_all(self):
        """Stop all workers."""
        for worker in self._workers:
            try:
                worker.stop()
            except Exception as e:
                logger.error("Failed to stop worker %s: %s", worker, e)
                
        # Also clean up adapters if possible
        for worker in self._workers:
            if hasattr(worker, 'adapter') and hasattr(worker.adapter, 'aclose'):
                import asyncio
                asyncio.create_task(worker.adapter.aclose())
