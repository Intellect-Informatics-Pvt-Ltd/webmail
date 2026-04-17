"""PSense Mail — Attachments API router.

Upload, download, and delete file attachments.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["attachments"])


def _get_facade():
    from app.main import get_registry
    from app.services.attachment_facade import AttachmentFacade
    return AttachmentFacade(file_storage=get_registry().file_storage)


@router.post("/attachments/upload")
async def upload_attachment(
    message_id: str = Query(..., description="Message or draft ID to attach to"),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload an attachment file."""
    content = await file.read()
    meta = await _get_facade().upload_attachment(
        user.user_id, message_id,
        file.filename or "unnamed", content,
        file.content_type or "application/octet-stream",
    )
    return meta.model_dump()


@router.get("/attachments/download")
async def download_attachment(
    path: str = Query(..., description="Storage path of the attachment"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """Download an attachment file."""
    content, content_type, filename = await _get_facade().download_attachment(user.user_id, path)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/attachments")
async def delete_attachment(
    path: str = Query(..., description="Storage path of the attachment"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """Delete an attachment file."""
    await _get_facade().delete_attachment(user.user_id, path)
    return {"status": "deleted"}
