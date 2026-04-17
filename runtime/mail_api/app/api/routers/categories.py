"""PSense Mail — Categories API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import CategoryCreateRequest, CategoryUpdateRequest
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.categories_facade import CategoriesFacade

router = APIRouter(prefix="/api/v1", tags=["categories"])
_facade = CategoriesFacade()


@router.get("/categories")
async def list_categories(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    cats = await _facade.list_categories(user.user_id)
    return [c.model_dump(by_alias=True) for c in cats]


@router.post("/categories", status_code=201)
async def create_category(body: CategoryCreateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    cat = await _facade.create_category(user.user_id, body)
    return cat.model_dump(by_alias=True)


@router.put("/categories/{cat_id}")
async def update_category(cat_id: str, body: CategoryUpdateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    cat = await _facade.update_category(user.user_id, cat_id, body)
    return cat.model_dump(by_alias=True)


@router.delete("/categories/{cat_id}", response_model=SuccessResponse)
async def delete_category(cat_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> SuccessResponse:
    await _facade.delete_category(user.user_id, cat_id)
    return SuccessResponse(message="Category deleted")
