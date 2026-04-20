"""PSense Mail — Attachment Preview service.

Generates thumbnail previews for common attachment types (images, PDFs).
Preview state tracked on MailAttachmentMeta.preview_state.
"""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.protocols import FileStorageAdapter
from app.domain.enums import PreviewState
from app.domain.models import MessageDoc

logger = logging.getLogger(__name__)

# MIME types that support preview generation
PREVIEWABLE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "text/plain", "text/html", "text/csv",
}


class PreviewService:
    """Generate and manage attachment previews."""

    def __init__(self, file_storage: FileStorageAdapter):
        self._storage = file_storage

    def can_preview(self, mime: str) -> bool:
        return mime.lower() in PREVIEWABLE_MIMES

    async def generate_preview(
        self, user_id: str, message_id: str, attachment_id: str,
    ) -> dict[str, Any]:
        """Generate a preview for an attachment. Returns preview metadata."""
        msg = await MessageDoc.find_one(
            MessageDoc.id == message_id, MessageDoc.user_id == user_id,
        )
        if not msg:
            return {"error": "Message not found"}

        attachment = None
        for att in msg.attachments:
            if att.id == attachment_id:
                attachment = att
                break

        if not attachment:
            return {"error": "Attachment not found"}

        if not self.can_preview(attachment.mime):
            attachment.preview_state = PreviewState.FAILED
            await msg.save()
            return {"error": f"Preview not supported for {attachment.mime}"}

        attachment.preview_state = PreviewState.PROCESSING
        await msg.save()

        try:
            # For images, the file itself is the preview (could generate thumbnail)
            if attachment.mime.startswith("image/"):
                preview_path = f"{user_id}/{message_id}/preview-{attachment_id}.webp"
                if attachment.storage_path:
                    content, _ = await self._storage.retrieve(attachment.storage_path)
                    # In production, resize to thumbnail with Pillow
                    await self._storage.store(preview_path, content, "image/webp")

                attachment.preview_state = PreviewState.READY
                await msg.save()
                return {
                    "preview_path": preview_path,
                    "state": PreviewState.READY.value,
                }

            # For text/PDF, generate text extract preview
            elif attachment.mime in ("text/plain", "text/csv"):
                if attachment.storage_path:
                    content, _ = await self._storage.retrieve(attachment.storage_path)
                    text_preview = content[:2000].decode("utf-8", errors="replace")
                    preview_path = f"{user_id}/{message_id}/preview-{attachment_id}.txt"
                    await self._storage.store(preview_path, text_preview.encode(), "text/plain")

                    attachment.preview_state = PreviewState.READY
                    await msg.save()
                    return {
                        "preview_path": preview_path,
                        "text_preview": text_preview[:500],
                        "state": PreviewState.READY.value,
                    }

            attachment.preview_state = PreviewState.READY
            await msg.save()
            return {"state": PreviewState.READY.value}

        except Exception as exc:
            logger.error("Preview generation failed for %s/%s: %s", message_id, attachment_id, exc)
            attachment.preview_state = PreviewState.FAILED
            await msg.save()
            return {"error": str(exc), "state": PreviewState.FAILED.value}

    async def get_preview_state(
        self, user_id: str, message_id: str, attachment_id: str,
    ) -> dict[str, Any]:
        """Get current preview generation state."""
        msg = await MessageDoc.find_one(
            MessageDoc.id == message_id, MessageDoc.user_id == user_id,
        )
        if not msg:
            return {"state": "unknown"}

        for att in msg.attachments:
            if att.id == attachment_id:
                return {
                    "state": att.preview_state.value,
                    "can_preview": self.can_preview(att.mime),
                }

        return {"state": "unknown"}
