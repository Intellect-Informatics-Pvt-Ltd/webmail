"""PSense Mail — Contacts API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.domain.responses import SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.contacts_facade import ContactsFacade

router = APIRouter(prefix="/api/v1", tags=["contacts"])
_facade = ContactsFacade()


@router.get("/contacts")
async def list_contacts(
    q: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await _facade.list_contacts(user.user_id, query=q, cursor=cursor, limit=limit)


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.get_contact(user.user_id, contact_id)
    return doc.model_dump(by_alias=True)


@router.post("/contacts", status_code=201)
async def create_contact(
    body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.create_contact(user.user_id, body)
    return doc.model_dump(by_alias=True)


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str, body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _facade.update_contact(user.user_id, contact_id, body)
    return doc.model_dump(by_alias=True)


@router.delete("/contacts/{contact_id}", response_model=SuccessResponse)
async def delete_contact(
    contact_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessResponse:
    await _facade.delete_contact(user.user_id, contact_id)
    return SuccessResponse(message="Contact deleted")


@router.post("/contacts/merge")
async def merge_contacts(
    body: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Merge contacts. Body: {"primary_id": "...", "secondary_ids": ["..."]}"""
    doc = await _facade.merge_contacts(
        user.user_id, body["primary_id"], body.get("secondary_ids", []),
    )
    return doc.model_dump(by_alias=True)
