"""PSense Mail — SearchFacade service.

Full-text search with structured operators (from:, to:, has:, is:, subject:)
matching the webmail UI's use-filtered-messages.ts logic.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from app.domain.models import MessageDoc, MailRecipient
from app.domain.requests import SearchRequest
from app.domain.responses import SearchHit, SearchResponse

logger = logging.getLogger(__name__)


def _parse_search_query(query: str) -> dict[str, Any]:
    """Parse structured search operators into MongoDB filter fields.

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
    """Search operations facade."""

    async def search_messages(
        self, user_id: str, request: SearchRequest,
    ) -> SearchResponse:
        """Search messages with structured filters and free-text."""
        mongo_filter: dict[str, Any] = {"user_id": user_id}

        # Parse query string for operators
        parsed: dict[str, Any] = {}
        if request.query:
            parsed = _parse_search_query(request.query)

        # Apply parsed operator filters
        if "sender_email" in parsed:
            mongo_filter["sender.email"] = {"$regex": parsed["sender_email"], "$options": "i"}
        if "recipient_email" in parsed:
            mongo_filter["recipients.email"] = {"$regex": parsed["recipient_email"], "$options": "i"}
        if "subject_contains" in parsed:
            mongo_filter["subject"] = {"$regex": parsed["subject_contains"], "$options": "i"}
        if "has_attachments" in parsed:
            mongo_filter["has_attachments"] = parsed["has_attachments"]
        if "has_mentions" in parsed:
            mongo_filter["has_mentions"] = parsed["has_mentions"]
        if "is_read" in parsed:
            mongo_filter["is_read"] = parsed["is_read"]
        if "is_flagged" in parsed:
            mongo_filter["is_flagged"] = parsed["is_flagged"]
        if "is_pinned" in parsed:
            mongo_filter["is_pinned"] = parsed["is_pinned"]
        if "is_draft" in parsed:
            mongo_filter["is_draft"] = parsed["is_draft"]
        if "folder_id" in parsed:
            mongo_filter["folder_id"] = parsed["folder_id"]
        if "category" in parsed:
            mongo_filter["categories"] = parsed["category"]

        # Free-text: match against subject, preview, and body_text
        if "free_text" in parsed:
            text = parsed["free_text"]
            mongo_filter["$or"] = [
                {"subject": {"$regex": text, "$options": "i"}},
                {"preview": {"$regex": text, "$options": "i"}},
                {"body_text": {"$regex": text, "$options": "i"}},
            ]

        # Apply explicit request filters (override parsed ones)
        if request.folder_id:
            mongo_filter["folder_id"] = request.folder_id
        if request.sender:
            mongo_filter["sender.email"] = {"$regex": request.sender, "$options": "i"}
        if request.recipient:
            mongo_filter["recipients.email"] = {"$regex": request.recipient, "$options": "i"}
        if request.subject:
            mongo_filter["subject"] = {"$regex": request.subject, "$options": "i"}
        if request.is_read is not None:
            mongo_filter["is_read"] = request.is_read
        if request.is_flagged is not None:
            mongo_filter["is_flagged"] = request.is_flagged
        if request.has_attachments is not None:
            mongo_filter["has_attachments"] = request.has_attachments
        if request.categories:
            mongo_filter["categories"] = {"$in": request.categories}
        if request.date_from:
            mongo_filter.setdefault("received_at", {})["$gte"] = request.date_from
        if request.date_to:
            mongo_filter.setdefault("received_at", {})["$lte"] = request.date_to

        # Cursor pagination
        if request.cursor:
            mongo_filter.setdefault("received_at", {})["$lt"] = datetime.fromisoformat(request.cursor)

        # Execute query
        docs = await MessageDoc.find(mongo_filter).sort(
            [("received_at", -1)]
        ).limit(request.limit + 1).to_list()

        has_more = len(docs) > request.limit
        if has_more:
            docs = docs[:request.limit]

        hits = [
            SearchHit(
                message_id=d.id, thread_id=d.thread_id,
                subject=d.subject, preview=d.preview, sender=d.sender,
                matched_fields=self._detect_matched_fields(d, parsed),
                received_at=d.received_at,
            )
            for d in docs
        ]

        next_cursor = None
        if has_more and docs and docs[-1].received_at:
            next_cursor = docs[-1].received_at.isoformat()

        total = await MessageDoc.find(mongo_filter).count()

        # Build facets
        facets = await self._build_facets(user_id, mongo_filter)

        return SearchResponse(
            hits=hits, next_cursor=next_cursor,
            total_estimate=total, facets=facets,
        )

    async def get_suggestions(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
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

    def _detect_matched_fields(self, msg: MessageDoc, parsed: dict[str, Any]) -> list[str]:
        """Detect which fields matched the search."""
        matched: list[str] = []
        text = parsed.get("free_text", "")
        if text:
            if text.lower() in msg.subject.lower():
                matched.append("subject")
            if text.lower() in msg.preview.lower():
                matched.append("preview")
            if msg.body_text and text.lower() in msg.body_text.lower():
                matched.append("body")
        if "sender_email" in parsed:
            matched.append("sender")
        return matched or ["subject"]

    async def _build_facets(self, user_id: str, base_filter: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """Build search facets (folder distribution, categories)."""
        # Simplified facets — count by folder
        facets: dict[str, list[dict[str, Any]]] = {"folders": [], "categories": []}

        # Only build facets if we have results
        all_docs = await MessageDoc.find(base_filter).to_list()
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
