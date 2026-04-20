"""PSense Mail — CalendarFacade service.

CRUD for calendar events with iCalendar UID dedup support.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.errors import NotFoundError
from app.domain.models import CalendarEventDoc

logger = logging.getLogger(__name__)


class CalendarFacade:
    """Calendar events CRUD facade."""

    async def list_events(
        self, user_id: str,
        start: datetime | None = None, end: datetime | None = None,
        calendar_id: str | None = None,
        cursor: str | None = None, limit: int = 100,
    ) -> dict[str, Any]:
        """List events with optional date range filter."""
        filters: dict[str, Any] = {"user_id": user_id, "deleted_at": None}
        if start:
            filters["end_time"] = {"$gte": start}
        if end:
            filters.setdefault("start_time", {})
            if isinstance(filters.get("start_time"), dict):
                filters["start_time"]["$lte"] = end
            else:
                filters["start_time"] = {"$lte": end}
        if calendar_id:
            filters["calendar_id"] = calendar_id
        if cursor:
            filters["_id"] = {"$gt": cursor}

        docs = await CalendarEventDoc.find(filters).sort(
            [("start_time", 1)]
        ).limit(limit + 1).to_list()

        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]

        return {
            "items": [d.model_dump(by_alias=True) for d in docs],
            "next_cursor": docs[-1].id if has_more and docs else None,
        }

    async def get_event(self, user_id: str, event_id: str) -> CalendarEventDoc:
        doc = await CalendarEventDoc.find_one(
            CalendarEventDoc.id == event_id, CalendarEventDoc.user_id == user_id,
        )
        if not doc or doc.deleted_at:
            raise NotFoundError("CalendarEvent", event_id)
        return doc

    async def create_event(
        self, user_id: str, data: dict[str, Any],
        tenant_id: str = "default", account_id: str = "",
    ) -> CalendarEventDoc:
        # iCalendar UID dedup
        ical_uid = data.get("ical_uid")
        if ical_uid:
            existing = await CalendarEventDoc.find_one(
                CalendarEventDoc.user_id == user_id,
                CalendarEventDoc.ical_uid == ical_uid,
            )
            if existing and not existing.deleted_at:
                return existing  # Idempotent — return existing

        doc = CalendarEventDoc(
            user_id=user_id,
            tenant_id=tenant_id,
            account_id=account_id or user_id,
            **{k: v for k, v in data.items() if k not in ("user_id", "tenant_id", "account_id")},
        )
        await doc.insert()
        return doc

    async def update_event(
        self, user_id: str, event_id: str, patch: dict[str, Any],
    ) -> CalendarEventDoc:
        doc = await self.get_event(user_id, event_id)
        for key, val in patch.items():
            if val is not None and hasattr(doc, key) and key not in ("id", "user_id", "tenant_id"):
                setattr(doc, key, val)
        doc.updated_at = datetime.now(timezone.utc)
        doc.version += 1
        await doc.save()
        return doc

    async def delete_event(self, user_id: str, event_id: str) -> None:
        doc = await self.get_event(user_id, event_id)
        doc.deleted_at = datetime.now(timezone.utc)
        await doc.save()

    async def import_ical(self, user_id: str, ical_data: str, tenant_id: str = "default", account_id: str = "") -> list[CalendarEventDoc]:
        """Import events from iCalendar data. Returns list of created/updated events."""
        # Basic iCalendar parsing — for production, use icalendar library
        events: list[CalendarEventDoc] = []
        # Placeholder: parse VCALENDAR/VEVENT blocks
        logger.info("iCalendar import for user %s (%d bytes)", user_id, len(ical_data))
        return events
