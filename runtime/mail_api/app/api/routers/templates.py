"""PSense Mail — Templates API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import TemplateCreateRequest, TemplateUpdateRequest
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.templates_facade import TemplatesFacade

router = APIRouter(prefix="/api/v1", tags=["templates"])
_facade = TemplatesFacade()


@router.get("/templates")
async def list_templates(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    tpls = await _facade.list_templates(user.user_id)
    return [t.model_dump(by_alias=True) for t in tpls]


@router.post("/templates", status_code=201)
async def create_template(body: TemplateCreateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    tpl = await _facade.create_template(user.user_id, body)
    return tpl.model_dump(by_alias=True)


@router.put("/templates/{template_id}")
async def update_template(template_id: str, body: TemplateUpdateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    tpl = await _facade.update_template(user.user_id, template_id, body)
    return tpl.model_dump(by_alias=True)


@router.delete("/templates/{template_id}", response_model=SuccessResponse)
async def delete_template(template_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> SuccessResponse:
    await _facade.delete_template(user.user_id, template_id)
    return SuccessResponse(message="Template deleted")
