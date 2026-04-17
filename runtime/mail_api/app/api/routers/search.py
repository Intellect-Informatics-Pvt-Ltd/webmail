"""PSense Mail — Search API router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.domain.requests import SearchRequest
from app.domain.responses import SearchResponse
from app.middleware.auth import AuthenticatedUser
from app.services.search_facade import SearchFacade

router = APIRouter(prefix="/api/v1", tags=["search"])
_facade = SearchFacade()


@router.post("/search/messages", response_model=SearchResponse)
async def search_messages(
    body: SearchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SearchResponse:
    return await _facade.search_messages(user.user_id, body)


@router.get("/search/suggest", response_model=list[str])
async def search_suggest(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[str]:
    return await _facade.get_suggestions(user.user_id, q, limit)
