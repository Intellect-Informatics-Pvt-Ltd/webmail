"""PSense Mail — AttachmentFacade service."""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.protocols import AVScannerAdapter, AVVerdict, FileStorageAdapter
from app.domain.enums import AvState
from app.domain.errors import NotFoundError, PolicyDeniedError, ValidationError
from app.domain.models import MessageDoc, MailAttachmentMeta

logger = logging.getLogger(__name__)


class AttachmentFacade:
    """Attachment upload/download/delete facade with AV scanning."""

    def __init__(self, file_storage: FileStorageAdapter, av_scanner: AVScannerAdapter | None = None):
        self._storage = file_storage
        self._av = av_scanner

    async def upload_attachment(
        self, user_id: str, message_id: str,
        filename: str, content: bytes, content_type: str,
    ) -> MailAttachmentMeta:
        """Upload an attachment and link it to a message/draft."""
        from ulid import ULID

        att_id = str(ULID())
        storage_path = f"{user_id}/{message_id}/{att_id}-{filename}"

        await self._storage.store(storage_path, content, content_type)

        # AV scan — set state to PENDING, then scan inline
        av_state = AvState.UNKNOWN
        if self._av:
            av_state = AvState.PENDING
            scan_result = await self._av.scan(content, filename)
            if scan_result.verdict == AVVerdict.CLEAN:
                av_state = AvState.CLEAN
            elif scan_result.verdict == AVVerdict.INFECTED:
                # Remove the infected file
                await self._storage.delete(storage_path)
                raise PolicyDeniedError(
                    f"Attachment '{filename}' rejected: malware detected ({scan_result.threat_name})"
                )
            else:
                av_state = AvState.PENDING  # Error — retry later

        meta = MailAttachmentMeta(
            id=att_id, name=filename, size=len(content),
            mime=content_type, storage_path=storage_path,
            av_state=av_state,
        )

        logger.info("Uploaded attachment %s (%d bytes) to %s", filename, len(content), storage_path)
        return meta

    async def download_attachment(
        self, user_id: str, attachment_path: str,
    ) -> tuple[bytes, str, str]:
        """Download an attachment. Returns (content, content_type, filename).
        Blocks download of INFECTED attachments."""
        # Verify path belongs to user
        if not attachment_path.startswith(f"{user_id}/"):
            raise ValidationError("Access denied to attachment")

        # Check AV state — block INFECTED downloads
        parts = attachment_path.split("/")
        if len(parts) >= 3:
            message_id = parts[1]
            att_id_filename = parts[2]
            att_id = att_id_filename.split("-", 1)[0] if "-" in att_id_filename else att_id_filename
            msg = await MessageDoc.find_one(
                MessageDoc.id == message_id, MessageDoc.user_id == user_id,
            )
            if msg:
                for att in msg.attachments:
                    if att.id == att_id and att.av_state == AvState.INFECTED:
                        raise PolicyDeniedError("Download blocked: attachment flagged as infected")

        content, content_type = await self._storage.retrieve(attachment_path)
        filename = attachment_path.rsplit("/", 1)[-1]
        # Strip ULID prefix from filename
        if "-" in filename:
            filename = filename.split("-", 1)[1]
        return content, content_type, filename

    async def delete_attachment(self, user_id: str, attachment_path: str) -> None:
        """Delete an attachment file."""
        if not attachment_path.startswith(f"{user_id}/"):
            raise ValidationError("Access denied to attachment")
        await self._storage.delete(attachment_path)

    async def list_attachments(self, user_id: str, message_id: str) -> list[MailAttachmentMeta]:
        """List attachments for a message."""
        msg = await MessageDoc.find_one(MessageDoc.id == message_id, MessageDoc.user_id == user_id)
        if not msg:
            raise NotFoundError("Message", message_id)
        return msg.attachments
