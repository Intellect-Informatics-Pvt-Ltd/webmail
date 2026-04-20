"""PSense Mail — AI Copilot router.

Endpoints for message summarisation, smart reply suggestions,
and priority scoring.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


def _get_facade():
    from app.main import get_registry
    from app.services.copilot_facade import CopilotFacade
    registry = get_registry()
    return CopilotFacade(llm=registry.llm)


@router.get("/messages/{message_id}/summary")
async def get_summary(
    message_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """Get AI-generated summary of a message (≤3 sentences)."""
    facade = _get_facade()
    return await facade.summarise_message(message_id, user.user_id)


@router.get("/messages/{message_id}/replies")
async def get_replies(
    message_id: str,
    count: int = 3,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Get smart reply suggestions for a message."""
    facade = _get_facade()
    return await facade.suggest_replies(message_id, user.user_id, count=count)


@router.get("/messages/{message_id}/priority")
async def get_priority(
    message_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get AI-generated priority score (0.0–1.0) and reason."""
    facade = _get_facade()
    return await facade.score_priority(message_id, user.user_id)
