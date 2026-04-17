"""PSense Mail — Signatures API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import SignatureCreateRequest, SignatureUpdateRequest
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.signatures_facade import SignaturesFacade

router = APIRouter(prefix="/api/v1", tags=["signatures"])
_facade = SignaturesFacade()


@router.get("/signatures")
async def list_signatures(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    sigs = await _facade.list_signatures(user.user_id)
    return [s.model_dump(by_alias=True) for s in sigs]


@router.post("/signatures", status_code=201)
async def create_signature(body: SignatureCreateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    sig = await _facade.create_signature(user.user_id, body)
    return sig.model_dump(by_alias=True)


@router.put("/signatures/{sig_id}")
async def update_signature(sig_id: str, body: SignatureUpdateRequest, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    sig = await _facade.update_signature(user.user_id, sig_id, body)
    return sig.model_dump(by_alias=True)


@router.post("/signatures/{sig_id}/default")
async def set_default_signature(sig_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    sig = await _facade.set_default(user.user_id, sig_id)
    return sig.model_dump(by_alias=True)


@router.delete("/signatures/{sig_id}", response_model=SuccessResponse)
async def delete_signature(sig_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> SuccessResponse:
    await _facade.delete_signature(user.user_id, sig_id)
    return SuccessResponse(message="Signature deleted")
