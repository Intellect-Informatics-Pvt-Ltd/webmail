"""PSense Mail — Drafts API router.

Draft lifecycle: create, update, save, discard, send.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import DraftCreateRequest, DraftPatchRequest, SendDraftRequest
from app.domain.responses import DeliveryReceipt, DraftResponse, SuccessResponse
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["drafts"])


def _get_facade():
    from app.main import get_registry
    from app.services.compose_facade import ComposeFacade
    from config.settings import get_settings
    registry = get_registry()
    settings = get_settings()
    return ComposeFacade(
        transport=registry.transport,
        default_from_address=settings.provider.mailpit.from_address,
    )


@router.get("/drafts", response_model=list[DraftResponse])
async def list_drafts(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[DraftResponse]:
    return await _get_facade().list_drafts(user.user_id)


@router.post("/drafts", response_model=DraftResponse, status_code=201)
async def create_draft(
    body: DraftCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DraftResponse:
    return await _get_facade().create_draft(user.user_id, body)


@router.patch("/drafts/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: str, body: DraftPatchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DraftResponse:
    return await _get_facade().update_draft(user.user_id, draft_id, body)


@router.post("/drafts/{draft_id}/save", response_model=DraftResponse)
async def save_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DraftResponse:
    return await _get_facade().save_draft(user.user_id, draft_id)


@router.delete("/drafts/{draft_id}", response_model=SuccessResponse)
async def discard_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessResponse:
    await _get_facade().discard_draft(user.user_id, draft_id)
    return SuccessResponse(message="Draft discarded")


@router.post("/drafts/{draft_id}/send", response_model=DeliveryReceipt)
async def send_draft(
    draft_id: str, body: SendDraftRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DeliveryReceipt:
    return await _get_facade().send_draft(
        user.user_id, draft_id, body or SendDraftRequest(),
        user_email=user.email, user_name=user.display_name,
    )


@router.post("/messages/{message_id}/retry", response_model=DeliveryReceipt)
async def retry_send(
    message_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DeliveryReceipt:
    return await _get_facade().retry_send(user.user_id, message_id)
