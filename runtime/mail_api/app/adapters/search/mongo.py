"""PSense Mail — MongoDB text search adapter.

Uses MongoDB's $text index and $regex for search. In production with
MongoDB Atlas, this can be upgraded to Atlas Search (Lucene-based).
"""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.protocols import AdapterHealthStatus

logger = logging.getLogger(__name__)


class MongoSearchAdapter:
    """MongoDB $text + $regex search adapter.

    Leverages the text indexes defined on MessageDoc for basic full-text
    search. For faceted search, uses MongoDB aggregation pipelines.
    """

    async def index_message(self, user_id: str, message_id: str, content: dict[str, Any]) -> None:
        # MongoDB text indexes are automatic — no explicit indexing needed.
        pass

    async def remove_message(self, user_id: str, message_id: str) -> None:
        # Handled by document deletion — no separate index to clean up.
        pass

    async def search(
        self, user_id: str, query: str,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        """Search messages using MongoDB queries.

        The actual search logic lives in SearchFacade which builds
        Beanie queries. This adapter is used for any provider-specific
        search features (e.g., Atlas Search in the future).
        """
        # Delegated to SearchFacade for now
        return {"hits": [], "next_cursor": None, "total_estimate": 0, "facets": {}}

    async def suggest(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
        return []

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="mongo-search", status="ok")
