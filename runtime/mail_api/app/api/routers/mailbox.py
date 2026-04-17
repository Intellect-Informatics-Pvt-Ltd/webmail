"""PSense Mail — Mailbox (folders & favorites) API router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import FolderCreateRequest, FolderRenameRequest
from app.domain.responses import FolderCountsResponse, FolderResponse, SuccessResponse
from app.middleware.auth import AuthenticatedUser
from app.services.mail_facade import MailFacade

router = APIRouter(prefix="/api/v1", tags=["mailbox"])
_facade = MailFacade()


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[FolderResponse]:
    return await _facade.list_folders(user.user_id)


@router.post("/folders", response_model=FolderResponse, status_code=201)
async def create_folder(
    body: FolderCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> FolderResponse:
    return await _facade.create_folder(user.user_id, body.name, body.parent_id)


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: str, body: FolderRenameRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> FolderResponse:
    return await _facade.rename_folder(user.user_id, folder_id, body.name)


@router.delete("/folders/{folder_id}", response_model=SuccessResponse)
async def delete_folder(
    folder_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessResponse:
    await _facade.delete_folder(user.user_id, folder_id)
    return SuccessResponse(message=f"Folder '{folder_id}' deleted")


@router.get("/folders/counts", response_model=FolderCountsResponse)
async def get_folder_counts(
    user: AuthenticatedUser = Depends(get_current_user),
) -> FolderCountsResponse:
    return await _facade.get_folder_counts(user.user_id)


@router.get("/folders/favorites", response_model=list[str])
async def list_favorites(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[str]:
    return await _facade.list_favorites(user.user_id)


@router.post("/folders/{folder_id}/favorite", response_model=list[str])
async def toggle_favorite(
    folder_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[str]:
    return await _facade.toggle_favorite(user.user_id, folder_id)
