"""PSense Mail — Multi-account inbound poller dispatcher.

Manages one InboundPollerWorker per active polling-capable account.
Supports dynamic account add/remove without restarting the application.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import AccountDoc
from app.workers.inbound_poller import InboundPollerWorker

if TYPE_CHECKING:
    from app.adapters.registry import AdapterRegistry
    from config.settings import Settings

logger = logging.getLogger(__name__)

# Provider kinds that support polling
_POLLING_PROVIDERS = {"pop3", "mailpit", "imap"}

# Graceful shutdown timeout (seconds)
_SHUTDOWN_TIMEOUT = 10


class InboundPollerDispatcher:
    """Manages one InboundPollerWorker per active polling account.

    On startup it queries AccountDoc for all active accounts whose
    provider supports polling and starts a worker for each.

    Exposes methods to dynamically add/remove accounts at runtime.
    """

    def __init__(self, settings: "Settings", registry: "AdapterRegistry"):
        self._settings = settings
        self._registry = registry
        self._workers: dict[str, InboundPollerWorker] = {}
        self._backoff: dict[str, float] = {}  # account_id -> current backoff seconds
        self._running = False
        self._watchdog_task: asyncio.Task | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Discover all polling-capable accounts and start workers."""
        self._running = True

        accounts = await AccountDoc.find(
            AccountDoc.deleted_at == None,  # noqa: E711
        ).to_list()

        started = 0
        for acct in accounts:
            if acct.provider.value in _POLLING_PROVIDERS:
                await self._start_worker(acct)
                started += 1

        logger.info(
            "InboundPollerDispatcher started %d worker(s) for %d account(s)",
            started, len(accounts),
        )

        # Start watchdog that restarts failed workers with backoff
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def stop(self) -> None:
        """Stop all managed workers within the shutdown timeout."""
        self._running = False
        if self._watchdog_task:
            self._watchdog_task.cancel()

        tasks = []
        for account_id, worker in self._workers.items():
            worker.stop()
            if worker._task:
                tasks.append(worker._task)

        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=_SHUTDOWN_TIMEOUT)
            for t in pending:
                t.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        self._workers.clear()
        logger.info("InboundPollerDispatcher stopped all workers")

    # ── Dynamic account management ───────────────────────────────────

    async def add_account(self, account_id: str) -> None:
        """Start a poller for a newly created account (if polling-capable)."""
        if account_id in self._workers:
            return

        acct = await AccountDoc.find_one(AccountDoc.id == account_id)
        if not acct or acct.provider.value not in _POLLING_PROVIDERS:
            return

        await self._start_worker(acct)
        logger.info("Dynamic poller started for account %s", account_id)

    async def remove_account(self, account_id: str) -> None:
        """Stop and remove the poller for a deleted account."""
        worker = self._workers.pop(account_id, None)
        if worker:
            worker.stop()
            if worker._task:
                try:
                    await asyncio.wait_for(asyncio.shield(worker._task), timeout=5)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
            logger.info("Dynamic poller stopped for account %s", account_id)

    # ── Internal ─────────────────────────────────────────────────────

    async def _start_worker(self, acct: AccountDoc) -> None:
        """Create and start a worker for a specific account."""
        adapter = self._registry.inbound
        worker = InboundPollerWorker(
            adapter=adapter,
            cache_user_id=acct.owner_user_id,
            poll_interval=self._settings.workers.sync_interval_seconds,
        )
        worker.start()
        self._workers[acct.id] = worker

    async def _watchdog_loop(self) -> None:
        """Periodically check worker health, restart failed ones with backoff."""
        while self._running:
            try:
                await asyncio.sleep(30)
                for account_id, worker in list(self._workers.items()):
                    if worker.last_poll_status == "error":
                        backoff = self._backoff.get(account_id, 60)
                        if worker.last_poll_at:
                            elapsed = (datetime.now(timezone.utc) - worker.last_poll_at).total_seconds()
                            if elapsed < backoff:
                                continue

                        logger.warning(
                            "Restarting failed poller for account %s (backoff=%.0fs)",
                            account_id, backoff,
                        )
                        worker.stop()
                        worker.start()
                        # Exponential backoff, capped at 3600s
                        self._backoff[account_id] = min(backoff * 2, 3600)
                    else:
                        # Reset backoff on success
                        self._backoff.pop(account_id, None)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog error: %s", exc)

    @property
    def worker_count(self) -> int:
        return len(self._workers)

    @property
    def workers(self) -> dict[str, InboundPollerWorker]:
        return dict(self._workers)
