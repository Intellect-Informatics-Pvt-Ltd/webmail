"""PSense Mail — MongoDB text search adapter.

Uses MongoDB's $text index and $regex for search. In production with
MongoDB Atlas, this can be upgraded to Atlas Search (Lucene-based).

This adapter owns all MongoDB query construction for search. The
SearchFacade delegates to this adapter and handles only response mapping.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.adapters.protocols import AdapterHealthStatus
from app.domain.models import MessageDoc

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

        Builds a MongoDB filter from the structured `filters` dict and
        the free-text `query` string, then executes against MessageDoc.
        """
        mongo_filter: dict[str, Any] = {"user_id": user_id}

        if filters:
            self._apply_filters(mongo_filter, filters)

        # Free-text: match against subject, preview, and body_text
        if query:
            mongo_filter["$or"] = [
                {"subject": {"$regex": query, "$options": "i"}},
                {"preview": {"$regex": query, "$options": "i"}},
                {"body_text": {"$regex": query, "$options": "i"}},
            ]

        # Cursor pagination
        if cursor:
            mongo_filter.setdefault("received_at", {})["$lt"] = datetime.fromisoformat(cursor)

        # Execute query
        docs = await MessageDoc.find(mongo_filter).sort(
            [("received_at", -1)]
        ).limit(limit + 1).to_list()

        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]

        next_cursor = None
        if has_more and docs and docs[-1].received_at:
            next_cursor = docs[-1].received_at.isoformat()

        total = await MessageDoc.find(mongo_filter).count()

        return {
            "hits": docs,
            "next_cursor": next_cursor,
            "total_estimate": total,
        }

    async def suggest(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
        """Get search suggestions based on partial input."""
        suggestions: list[str] = []

        if len(partial) < 2:
            return suggestions

        # Suggest from subjects
        docs = await MessageDoc.find(
            MessageDoc.user_id == user_id,
            {"subject": {"$regex": partial, "$options": "i"}},
        ).limit(limit).to_list()

        seen: set[str] = set()
        for d in docs:
            if d.subject not in seen:
                suggestions.append(d.subject)
                seen.add(d.subject)

        # Suggest from senders
        sender_docs = await MessageDoc.find(
            MessageDoc.user_id == user_id,
            {"sender.email": {"$regex": partial, "$options": "i"}},
        ).limit(5).to_list()

        for d in sender_docs:
            key = f"from:{d.sender.email}"
            if key not in seen:
                suggestions.append(key)
                seen.add(key)

        return suggestions[:limit]

    async def build_facets(
        self, user_id: str, mongo_filter: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build search facets (folder distribution, categories)."""
        facets: dict[str, list[dict[str, Any]]] = {"folders": [], "categories": []}

        all_docs = await MessageDoc.find(mongo_filter).to_list()
        if not all_docs:
            return facets

        folder_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        for d in all_docs:
            folder_counts[d.folder_id] = folder_counts.get(d.folder_id, 0) + 1
            for c in d.categories:
                cat_counts[c] = cat_counts.get(c, 0) + 1

        facets["folders"] = [{"id": k, "count": v} for k, v in sorted(folder_counts.items(), key=lambda x: -x[1])]
        facets["categories"] = [{"id": k, "count": v} for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])]

        return facets

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="mongo-search", status="ok")

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _apply_filters(mongo_filter: dict[str, Any], filters: dict[str, Any]) -> None:
        """Apply structured search filters to a MongoDB query dict."""
        if "sender_email" in filters:
            mongo_filter["sender.email"] = {"$regex": filters["sender_email"], "$options": "i"}
        if "recipient_email" in filters:
            mongo_filter["recipients.email"] = {"$regex": filters["recipient_email"], "$options": "i"}
        if "subject_contains" in filters:
            mongo_filter["subject"] = {"$regex": filters["subject_contains"], "$options": "i"}
        if "has_attachments" in filters:
            mongo_filter["has_attachments"] = filters["has_attachments"]
        if "has_mentions" in filters:
            mongo_filter["has_mentions"] = filters["has_mentions"]
        if "is_read" in filters:
            mongo_filter["is_read"] = filters["is_read"]
        if "is_flagged" in filters:
            mongo_filter["is_flagged"] = filters["is_flagged"]
        if "is_pinned" in filters:
            mongo_filter["is_pinned"] = filters["is_pinned"]
        if "is_draft" in filters:
            mongo_filter["is_draft"] = filters["is_draft"]
        if "folder_id" in filters:
            mongo_filter["folder_id"] = filters["folder_id"]
        if "category" in filters:
            mongo_filter["categories"] = filters["category"]
        if "categories_in" in filters:
            mongo_filter["categories"] = {"$in": filters["categories_in"]}
        if "date_from" in filters:
            mongo_filter.setdefault("received_at", {})["$gte"] = filters["date_from"]
        if "date_to" in filters:
            mongo_filter.setdefault("received_at", {})["$lte"] = filters["date_to"]
