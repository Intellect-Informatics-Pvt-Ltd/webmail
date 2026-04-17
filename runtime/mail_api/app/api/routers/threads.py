"""PSense Mail — Threads API router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.responses import ThreadDetail
from app.middleware.auth import AuthenticatedUser
from app.services.mail_facade import MailFacade

router = APIRouter(prefix="/api/v1", tags=["threads"])
_facade = MailFacade()


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
async def get_thread(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ThreadDetail:
    return await _facade.get_thread(user.user_id, thread_id)
