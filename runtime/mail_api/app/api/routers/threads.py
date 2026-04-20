"""PSense Mail — Threads API router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.domain.responses import CursorPage, ThreadDetail, ThreadSummary
from app.middleware.auth import AuthenticatedUser
from app.services.mail_facade import MailFacade

router = APIRouter(prefix="/api/v1", tags=["threads"])
_facade = MailFacade()


@router.get("/threads", response_model=CursorPage[ThreadSummary])
async def list_threads(
    folder_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CursorPage[ThreadSummary]:
    return await _facade.list_threads(user.user_id, folder_id=folder_id, cursor=cursor, limit=limit)


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
async def get_thread(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ThreadDetail:
    return await _facade.get_thread(user.user_id, thread_id)
