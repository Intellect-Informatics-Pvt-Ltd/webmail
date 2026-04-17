"""PSense Mail — Rules API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import RuleCreateRequest, RuleUpdateRequest
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.rules_facade import RulesFacade

router = APIRouter(prefix="/api/v1", tags=["rules"])
_facade = RulesFacade()


@router.get("/rules")
async def list_rules(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    rules = await _facade.list_rules(user.user_id)
    return [r.model_dump(by_alias=True) for r in rules]


@router.post("/rules", status_code=201)
async def create_rule(
    body: RuleCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    rule = await _facade.create_rule(user.user_id, body)
    return rule.model_dump(by_alias=True)


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str, body: RuleUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    rule = await _facade.update_rule(user.user_id, rule_id, body)
    return rule.model_dump(by_alias=True)


@router.delete("/rules/{rule_id}", response_model=SuccessResponse)
async def delete_rule(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessResponse:
    await _facade.delete_rule(user.user_id, rule_id)
    return SuccessResponse(message="Rule deleted")
