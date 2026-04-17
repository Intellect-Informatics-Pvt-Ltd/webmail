"""PSense Mail — Messages API router.

Message listing, detail, and bulk actions.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.domain.requests import MessageActionRequest, MessageListQuery
from app.domain.responses import BulkActionResult, CursorPage, MessageDetail, MessageSummary
from app.middleware.auth import AuthenticatedUser
from app.services.mail_facade import MailFacade

router = APIRouter(prefix="/api/v1", tags=["messages"])
_facade = MailFacade()


@router.get("/messages", response_model=CursorPage[MessageSummary])
async def list_messages(
    folder_id: str | None = None,
    category_id: str | None = None,
    is_read: bool | None = None,
    is_flagged: bool | None = None,
    is_focused: bool | None = None,
    has_attachments: bool | None = None,
    has_mentions: bool | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = "received_at",
    sort_order: str = "desc",
    user: AuthenticatedUser = Depends(get_current_user),
) -> CursorPage[MessageSummary]:
    query = MessageListQuery(
        folder_id=folder_id, category_id=category_id,
        is_read=is_read, is_flagged=is_flagged, is_focused=is_focused,
        has_attachments=has_attachments, has_mentions=has_mentions,
        cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order,
    )
    return await _facade.list_messages(user.user_id, query)


@router.get("/messages/{message_id}", response_model=MessageDetail)
async def get_message(
    message_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> MessageDetail:
    return await _facade.get_message(user.user_id, message_id)


@router.post("/messages/actions", response_model=BulkActionResult)
async def apply_message_actions(
    body: MessageActionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> BulkActionResult:
    return await _facade.apply_action(user.user_id, body)
