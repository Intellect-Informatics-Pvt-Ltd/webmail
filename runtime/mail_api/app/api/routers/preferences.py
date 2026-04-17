"""PSense Mail — Preferences API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import PreferencesPatchRequest
from app.middleware.auth import AuthenticatedUser
from app.services.preferences_facade import PreferencesFacade

router = APIRouter(prefix="/api/v1", tags=["preferences"])
_facade = PreferencesFacade()


@router.get("/preferences")
async def get_preferences(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    prefs = await _facade.get_preferences(user.user_id)
    return prefs.model_dump(by_alias=True)


@router.patch("/preferences")
async def update_preferences(
    body: PreferencesPatchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    prefs = await _facade.update_preferences(user.user_id, body.model_dump(exclude_none=True))
    return prefs.model_dump(by_alias=True)
