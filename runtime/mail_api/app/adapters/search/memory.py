"""PSense Mail — In-memory search adapter.

Simple substring search for dev/testing. No indexing overhead.
"""
from __future__ import annotations

from typing import Any

from app.adapters.protocols import AdapterHealthStatus


class MemorySearchAdapter:
    """In-memory search — scans documents directly via MongoDB queries.

    For the in-memory database backend, search is handled by Beanie queries
    in the SearchFacade directly. This adapter is a no-op placeholder that
    satisfies the protocol.
    """

    async def index_message(self, user_id: str, message_id: str, content: dict[str, Any]) -> None:
        pass  # No separate index in memory mode

    async def remove_message(self, user_id: str, message_id: str) -> None:
        pass

    async def search(
        self, user_id: str, query: str,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        # The SearchFacade handles in-memory search via Beanie queries
        return {"hits": [], "next_cursor": None, "total_estimate": 0, "facets": {}}

    async def suggest(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
        return []

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="memory-search", status="ok")
