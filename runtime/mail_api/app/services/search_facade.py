"""PSense Mail — SearchFacade service.

Full-text search with structured operators (from:, to:, has:, is:, subject:)
matching the webmail UI's use-filtered-messages.ts logic.

Delegates all query execution to the injected SearchAdapter (Mongo or Memory).
The facade owns only query parsing, request-to-filter mapping, and response mapping.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.adapters.protocols import SearchAdapter
from app.domain.models import MessageDoc
from app.domain.requests import SearchRequest
from app.domain.responses import SearchHit, SearchResponse

logger = logging.getLogger(__name__)


def _parse_search_query(query: str) -> dict[str, Any]:
    """Parse structured search operators into filter fields.

    Supports: from:, to:, subject:, has:attachment, is:read/unread/flagged/pinned
    Everything else becomes a free-text substring match.
    """
    filters: dict[str, Any] = {}
    remainder_parts: list[str] = []

    tokens = re.findall(r'(\w+:[^\s]+|"[^"]+"|\S+)', query)

    for token in tokens:
        if token.startswith("from:"):
            filters["sender_email"] = token[5:].strip('"')
        elif token.startswith("to:"):
            filters["recipient_email"] = token[3:].strip('"')
        elif token.startswith("subject:"):
            filters["subject_contains"] = token[8:].strip('"')
        elif token.startswith("has:"):
            val = token[4:]
            if val in ("attachment", "attachments"):
                filters["has_attachments"] = True
            elif val == "mentions":
                filters["has_mentions"] = True
        elif token.startswith("is:"):
            val = token[3:]
            if val == "read":
                filters["is_read"] = True
            elif val == "unread":
                filters["is_read"] = False
            elif val == "flagged":
                filters["is_flagged"] = True
            elif val == "pinned":
                filters["is_pinned"] = True
            elif val == "draft":
                filters["is_draft"] = True
        elif token.startswith("in:"):
            filters["folder_id"] = token[3:]
        elif token.startswith("category:"):
            filters["category"] = token[9:]
        else:
            remainder_parts.append(token.strip('"'))

    if remainder_parts:
        filters["free_text"] = " ".join(remainder_parts)

    return filters


class SearchFacade:
    """Search operations facade — delegates query execution to SearchAdapter."""

    def __init__(self, search_adapter: SearchAdapter | None = None):
        self._search_adapter = search_adapter

    async def search_messages(
        self, user_id: str, request: SearchRequest,
    ) -> SearchResponse:
        """Search messages with structured filters and free-text."""
        if not self._search_adapter:
            raise RuntimeError("SearchFacade requires a SearchAdapter")

        # Parse query string for operators
        parsed: dict[str, Any] = {}
        free_text = ""
        if request.query:
            parsed = _parse_search_query(request.query)
            free_text = parsed.pop("free_text", "")

        # Merge explicit request filters (override parsed ones)
        if request.folder_id:
            parsed["folder_id"] = request.folder_id
        if request.sender:
            parsed["sender_email"] = request.sender
        if request.recipient:
            parsed["recipient_email"] = request.recipient
        if request.subject:
            parsed["subject_contains"] = request.subject
        if request.is_read is not None:
            parsed["is_read"] = request.is_read
        if request.is_flagged is not None:
            parsed["is_flagged"] = request.is_flagged
        if request.has_attachments is not None:
            parsed["has_attachments"] = request.has_attachments
        if request.categories:
            parsed["categories_in"] = request.categories
        if request.date_from:
            parsed["date_from"] = request.date_from
        if request.date_to:
            parsed["date_to"] = request.date_to

        # Delegate to adapter
        result = await self._search_adapter.search(
            user_id=user_id,
            query=free_text,
            filters=parsed if parsed else None,
            cursor=request.cursor,
            limit=request.limit,
        )

        # Map adapter result docs to SearchHit responses
        docs: list[MessageDoc] = result.get("hits", [])
        hits = [
            SearchHit(
                message_id=d.id, thread_id=d.thread_id,
                subject=d.subject, preview=d.preview, sender=d.sender,
                matched_fields=self._detect_matched_fields(d, free_text, parsed),
                received_at=d.received_at,
            )
            for d in docs
        ]

        # Build facets via adapter (uses same filter minus cursor for full facet counts)
        facet_filter: dict[str, Any] = {"user_id": user_id}
        if parsed:
            # Re-apply filters for facet query (adapters handle this internally)
            facet_filter.update({"_parsed": parsed})
        facets = await self._search_adapter.build_facets(user_id, {"user_id": user_id})

        return SearchResponse(
            hits=hits,
            next_cursor=result.get("next_cursor"),
            total_estimate=result.get("total_estimate", 0),
            facets=facets,
        )

    async def get_suggestions(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
        """Get search suggestions based on partial input."""
        if not self._search_adapter:
            raise RuntimeError("SearchFacade requires a SearchAdapter")
        return await self._search_adapter.suggest(user_id, partial, limit)

    @staticmethod
    def _detect_matched_fields(msg: MessageDoc, free_text: str, parsed: dict[str, Any]) -> list[str]:
        """Detect which fields matched the search."""
        matched: list[str] = []
        if free_text:
            if free_text.lower() in msg.subject.lower():
                matched.append("subject")
            if free_text.lower() in msg.preview.lower():
                matched.append("preview")
            if msg.body_text and free_text.lower() in msg.body_text.lower():
                matched.append("body")
        if "sender_email" in parsed:
            matched.append("sender")
        return matched or ["subject"]
