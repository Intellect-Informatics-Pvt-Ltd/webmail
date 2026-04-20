"""PSense Mail — Calendar API router."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.calendar_facade import CalendarFacade

router = APIRouter(prefix="/api/v1", tags=["calendar"])
_facade = CalendarFacade()


@router.get("/calendar/events")
async def list_events(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    calendar_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await _facade.list_events(
        user.user_id, start=start, end=end,
        calendar_id=calendar_id, cursor=cursor, limit=limit,
    )


@router.get("/calendar/events/{event_id}")
async def get_event(
    event_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.get_event(user.user_id, event_id)
    return doc.model_dump(by_alias=True)


@router.post("/calendar/events", status_code=201)
async def create_event(
    body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.create_event(user.user_id, body)
    return doc.model_dump(by_alias=True)


@router.patch("/calendar/events/{event_id}")
async def update_event(
    event_id: str, body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.update_event(user.user_id, event_id, body)
    return doc.model_dump(by_alias=True)


@router.delete("/calendar/events/{event_id}", response_model=SuccessResponse)
async def delete_event(
    event_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessResponse:
    await _facade.delete_event(user.user_id, event_id)
    return SuccessResponse(message="Event deleted")


@router.post("/calendar/import")
async def import_ical(
    body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Import iCalendar data. Body: {"ical_data": "BEGIN:VCALENDAR..."}"""
    events = await _facade.import_ical(user.user_id, body.get("ical_data", ""))
    return {"imported": len(events)}
