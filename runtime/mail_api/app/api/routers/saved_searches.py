"""PSense Mail — Saved Searches API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import SavedSearchCreateRequest
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.saved_searches_facade import SavedSearchesFacade

router = APIRouter(prefix="/api/v1", tags=["saved_searches"])
_facade = SavedSearchesFacade()


@router.get("/saved-searches")
async def list_saved_searches(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    ss = await _facade.list_saved_searches(user.user_id)
    return [s.model_dump(by_alias=True) for s in ss]


@router.post("/saved-searches", status_code=201)
async def create_saved_search(body: SavedSearchCreateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    ss = await _facade.create_saved_search(user.user_id, body)
    return ss.model_dump(by_alias=True)


@router.delete("/saved-searches/{search_id}", response_model=SuccessResponse)
async def delete_saved_search(search_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> SuccessResponse:
    await _facade.delete_saved_search(user.user_id, search_id)
    return SuccessResponse(message="Saved search deleted")
