"""PSense Mail — MailFacade service.

Core mail operations: messages, folders, favorites, threads.
Maps every Zustand mail-store action to a server-side operation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.enums import FolderKind, Importance, MessageAction
from app.domain.errors import NotFoundError, ValidationError
from app.domain.models import (
    CategoryDoc,
    FavoritesDoc,
    FolderDoc,
    MailAttachmentMeta,
    MessageDoc,
    ThreadDoc,
)
from app.domain.requests import MessageActionRequest, MessageListQuery
from app.domain.responses import (
    AttachmentSummary,
    BulkActionResult,
    CursorPage,
    FolderCountsResponse,
    FolderResponse,
    MessageDetail,
    MessageSummary,
    ThreadDetail,
)

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _msg_to_summary(m: MessageDoc) -> MessageSummary:
    return MessageSummary(
        id=m.id, thread_id=m.thread_id, folder_id=m.folder_id,
        subject=m.subject, preview=m.preview, sender=m.sender,
        recipients=m.recipients, received_at=m.received_at,
        is_read=m.is_read, is_flagged=m.is_flagged, is_pinned=m.is_pinned,
        has_attachments=m.has_attachments, has_mentions=m.has_mentions,
        importance=m.importance.value, categories=m.categories,
        is_draft=m.is_draft, is_focused=m.is_focused,
        snoozed_until=m.snoozed_until, scheduled_for=m.scheduled_for,
        trust_verified=m.trust_verified,
    )


def _msg_to_detail(m: MessageDoc) -> MessageDetail:
    return MessageDetail(
        id=m.id, thread_id=m.thread_id, folder_id=m.folder_id,
        subject=m.subject, preview=m.preview, sender=m.sender,
        recipients=m.recipients, received_at=m.received_at,
        is_read=m.is_read, is_flagged=m.is_flagged, is_pinned=m.is_pinned,
        has_attachments=m.has_attachments, has_mentions=m.has_mentions,
        importance=m.importance.value, categories=m.categories,
        is_draft=m.is_draft, is_focused=m.is_focused,
        snoozed_until=m.snoozed_until, scheduled_for=m.scheduled_for,
        trust_verified=m.trust_verified,
        body_html=m.body_html, body_text=m.body_text,
        cc=m.cc, bcc=m.bcc,
        attachments=[AttachmentSummary(id=a.id, name=a.name, size=a.size, mime=a.mime) for a in m.attachments],
        in_reply_to_id=m.in_reply_to_id,
        delivery_state=m.delivery_state, version=m.version,
    )


def _folder_to_response(f: FolderDoc, unread: int = 0, total: int = 0) -> FolderResponse:
    return FolderResponse(
        id=f.id, name=f.name, kind=f.kind.value, system=f.system,
        parent_id=f.parent_id, sort_order=f.sort_order, icon=f.icon,
        unread_count=unread, total_count=total,
    )


# ── MailFacade ───────────────────────────────────────────────────────────────


class MailFacade:
    """Core mail operations facade."""

    # ── Messages ─────────────────────────────────────────────────────────

    async def list_messages(
        self, user_id: str, query: MessageListQuery,
    ) -> CursorPage[MessageSummary]:
        """List messages with filtering, sorting, and cursor pagination."""
        filters: dict[str, Any] = {"user_id": user_id}

        if query.folder_id:
            # Special handling for virtual folders
            if query.folder_id == "flagged":
                filters["is_flagged"] = True
                filters["folder_id"] = {"$ne": "deleted"}
            elif query.folder_id == "focused":
                filters["folder_id"] = "inbox"
                filters["is_focused"] = True
            elif query.folder_id == "other":
                filters["folder_id"] = "inbox"
                filters["is_focused"] = False
            else:
                filters["folder_id"] = query.folder_id

        if query.category_id:
            filters["categories"] = query.category_id
        if query.is_read is not None:
            filters["is_read"] = query.is_read
        if query.is_flagged is not None:
            filters["is_flagged"] = query.is_flagged
        if query.is_focused is not None:
            filters["is_focused"] = query.is_focused
        if query.has_attachments is not None:
            filters["has_attachments"] = query.has_attachments
        if query.has_mentions is not None:
            filters["has_mentions"] = query.has_mentions

        # Cursor-based pagination
        if query.cursor:
            if query.sort_order == "desc":
                filters["received_at"] = {"$lt": datetime.fromisoformat(query.cursor)}
            else:
                filters["received_at"] = {"$gt": datetime.fromisoformat(query.cursor)}

        # Sort: pinned first, then by sort_by
        sort_dir = -1 if query.sort_order == "desc" else 1
        sort_spec = [("is_pinned", -1), (query.sort_by, sort_dir)]

        docs = await MessageDoc.find(filters).sort(sort_spec).limit(query.limit + 1).to_list()

        has_more = len(docs) > query.limit
        if has_more:
            docs = docs[:query.limit]

        items = [_msg_to_summary(d) for d in docs]
        next_cursor = None
        if has_more and docs:
            last = docs[-1]
            if last.received_at:
                next_cursor = last.received_at.isoformat()

        total = await MessageDoc.find(filters).count()

        return CursorPage(items=items, next_cursor=next_cursor, total_estimate=total)

    async def get_message(self, user_id: str, message_id: str) -> MessageDetail:
        """Get full message detail."""
        doc = await MessageDoc.find_one(MessageDoc.id == message_id, MessageDoc.user_id == user_id)
        if not doc:
            raise NotFoundError("Message", message_id)

        # Auto-mark as read
        if not doc.is_read:
            doc.is_read = True
            doc.updated_at = datetime.now(timezone.utc)
            await doc.save()

        return _msg_to_detail(doc)

    async def get_thread(self, user_id: str, thread_id: str) -> ThreadDetail:
        """Get thread with all its messages."""
        thread = await ThreadDoc.find_one(ThreadDoc.id == thread_id, ThreadDoc.user_id == user_id)
        if not thread:
            raise NotFoundError("Thread", thread_id)

        messages = await MessageDoc.find(
            MessageDoc.user_id == user_id, MessageDoc.thread_id == thread_id,
        ).sort([("received_at", 1)]).to_list()

        return ThreadDetail(
            id=thread.id, subject=thread.subject, folder_id=thread.folder_id,
            participant_emails=thread.participant_emails,
            last_message_at=thread.last_message_at,
            unread_count=thread.unread_count, total_count=thread.total_count,
            has_attachments=thread.has_attachments, is_flagged=thread.is_flagged,
            messages=[_msg_to_detail(m) for m in messages],
        )

    async def apply_action(
        self, user_id: str, request: MessageActionRequest,
    ) -> BulkActionResult:
        """Apply an action to one or more messages (bulk)."""
        succeeded: list[str] = []
        failed: dict[str, str] = {}

        for msg_id in request.message_ids:
            try:
                doc = await MessageDoc.find_one(MessageDoc.id == msg_id, MessageDoc.user_id == user_id)
                if not doc:
                    failed[msg_id] = "Not found"
                    continue

                action = request.action
                if action == MessageAction.MARK_READ:
                    doc.is_read = True
                elif action == MessageAction.MARK_UNREAD:
                    doc.is_read = False
                elif action == MessageAction.FLAG:
                    doc.is_flagged = True
                elif action == MessageAction.UNFLAG:
                    doc.is_flagged = False
                elif action == MessageAction.PIN:
                    doc.is_pinned = True
                elif action == MessageAction.UNPIN:
                    doc.is_pinned = False
                elif action == MessageAction.ARCHIVE:
                    doc.folder_id = "archive"
                elif action == MessageAction.DELETE:
                    doc.folder_id = "deleted"
                elif action == MessageAction.RESTORE:
                    doc.folder_id = "inbox"
                elif action == MessageAction.MOVE:
                    if not request.destination_folder_id:
                        failed[msg_id] = "destination_folder_id required for move"
                        continue
                    doc.folder_id = request.destination_folder_id
                elif action == MessageAction.SNOOZE:
                    if not request.snooze_until:
                        failed[msg_id] = "snooze_until required for snooze"
                        continue
                    doc.folder_id = "snoozed"
                    doc.snoozed_until = request.snooze_until
                elif action == MessageAction.UNSNOOZE:
                    doc.folder_id = "inbox"
                    doc.snoozed_until = None
                elif action == MessageAction.CATEGORIZE:
                    for cat_id in request.category_ids:
                        if cat_id not in doc.categories:
                            doc.categories.append(cat_id)
                elif action == MessageAction.UNCATEGORIZE:
                    doc.categories = [c for c in doc.categories if c not in request.category_ids]

                doc.updated_at = datetime.now(timezone.utc)
                doc.version += 1
                await doc.save()
                succeeded.append(msg_id)

            except Exception as e:
                failed[msg_id] = str(e)

        # Update thread aggregates for affected threads
        affected_threads = set()
        for msg_id in succeeded:
            doc = await MessageDoc.find_one(MessageDoc.id == msg_id, MessageDoc.user_id == user_id)
            if doc:
                affected_threads.add(doc.thread_id)
        for tid in affected_threads:
            await self._refresh_thread(user_id, tid)

        return BulkActionResult(succeeded_ids=succeeded, failed=failed)

    async def upsert_message(self, user_id: str, message: MessageDoc) -> MessageDoc:
        """Create or update a message."""
        existing = await MessageDoc.find_one(MessageDoc.id == message.id, MessageDoc.user_id == user_id)
        if existing:
            update_data = message.model_dump(exclude={"id", "user_id", "created_at"})
            for key, val in update_data.items():
                setattr(existing, key, val)
            existing.updated_at = datetime.now(timezone.utc)
            existing.version += 1
            await existing.save()
            return existing
        else:
            message.user_id = user_id
            await message.insert()
            return message

    # ── Folders ──────────────────────────────────────────────────────────

    async def list_folders(self, user_id: str) -> list[FolderResponse]:
        """List all folders with unread/total counts."""
        folders = await FolderDoc.find(FolderDoc.user_id == user_id).sort([("sort_order", 1)]).to_list()

        result: list[FolderResponse] = []
        for f in folders:
            if f.system and f.kind in (FolderKind.FOCUSED, FolderKind.OTHER, FolderKind.FLAGGED):
                # Virtual folders — compute counts differently
                if f.kind == FolderKind.FLAGGED:
                    total = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.is_flagged == True,  # noqa: E712
                        MessageDoc.folder_id != "deleted",
                    ).count()
                    unread = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.is_flagged == True,  # noqa: E712
                        MessageDoc.is_read == False, MessageDoc.folder_id != "deleted",  # noqa: E712
                    ).count()
                elif f.kind == FolderKind.FOCUSED:
                    total = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.folder_id == "inbox",
                        MessageDoc.is_focused == True,  # noqa: E712
                    ).count()
                    unread = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.folder_id == "inbox",
                        MessageDoc.is_focused == True, MessageDoc.is_read == False,  # noqa: E712
                    ).count()
                else:  # OTHER
                    total = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.folder_id == "inbox",
                        MessageDoc.is_focused == False,  # noqa: E712
                    ).count()
                    unread = await MessageDoc.find(
                        MessageDoc.user_id == user_id, MessageDoc.folder_id == "inbox",
                        MessageDoc.is_focused == False, MessageDoc.is_read == False,  # noqa: E712
                    ).count()
            else:
                total = await MessageDoc.find(
                    MessageDoc.user_id == user_id, MessageDoc.folder_id == f.id,
                ).count()
                unread = await MessageDoc.find(
                    MessageDoc.user_id == user_id, MessageDoc.folder_id == f.id,
                    MessageDoc.is_read == False,  # noqa: E712
                ).count()

            result.append(_folder_to_response(f, unread=unread, total=total))

        return result

    async def create_folder(self, user_id: str, name: str, parent_id: str | None = None) -> FolderResponse:
        """Create a custom folder."""
        folder = FolderDoc(user_id=user_id, name=name, kind=FolderKind.CUSTOM, parent_id=parent_id)
        await folder.insert()
        return _folder_to_response(folder)

    async def rename_folder(self, user_id: str, folder_id: str, name: str) -> FolderResponse:
        """Rename a folder."""
        folder = await FolderDoc.find_one(FolderDoc.id == folder_id, FolderDoc.user_id == user_id)
        if not folder:
            raise NotFoundError("Folder", folder_id)
        if folder.system:
            raise ValidationError("Cannot rename system folders")
        folder.name = name
        await folder.save()
        return _folder_to_response(folder)

    async def delete_folder(self, user_id: str, folder_id: str) -> None:
        """Delete a custom folder. Moves contained messages to inbox."""
        folder = await FolderDoc.find_one(FolderDoc.id == folder_id, FolderDoc.user_id == user_id)
        if not folder:
            raise NotFoundError("Folder", folder_id)
        if folder.system:
            raise ValidationError("Cannot delete system folders")

        # Move messages to inbox
        await MessageDoc.find(
            MessageDoc.user_id == user_id, MessageDoc.folder_id == folder_id,
        ).update_many({"$set": {"folder_id": "inbox"}})

        # Remove from favorites
        fav = await FavoritesDoc.find_one(FavoritesDoc.id == user_id)
        if fav and folder_id in fav.folder_ids:
            fav.folder_ids.remove(folder_id)
            await fav.save()

        await folder.delete()

    async def get_folder_counts(self, user_id: str) -> FolderCountsResponse:
        """Get unread/total counts for all folders."""
        folders = await self.list_folders(user_id)
        counts = {}
        for f in folders:
            counts[f.id] = {"unread": f.unread_count, "total": f.total_count}
        return FolderCountsResponse(counts=counts)

    # ── Favorites ────────────────────────────────────────────────────────

    async def list_favorites(self, user_id: str) -> list[str]:
        """Get list of favorite folder IDs."""
        fav = await FavoritesDoc.find_one(FavoritesDoc.id == user_id)
        return fav.folder_ids if fav else []

    async def toggle_favorite(self, user_id: str, folder_id: str) -> list[str]:
        """Toggle a folder's favorite status."""
        fav = await FavoritesDoc.find_one(FavoritesDoc.id == user_id)
        if not fav:
            fav = FavoritesDoc(id=user_id, folder_ids=[folder_id])
            await fav.insert()
        elif folder_id in fav.folder_ids:
            fav.folder_ids.remove(folder_id)
            await fav.save()
        else:
            fav.folder_ids.append(folder_id)
            await fav.save()
        return fav.folder_ids

    # ── Thread refresh ───────────────────────────────────────────────────

    async def _refresh_thread(self, user_id: str, thread_id: str) -> None:
        """Recompute thread aggregates from its messages."""
        messages = await MessageDoc.find(
            MessageDoc.user_id == user_id, MessageDoc.thread_id == thread_id,
        ).to_list()
        if not messages:
            await ThreadDoc.find_one(ThreadDoc.id == thread_id, ThreadDoc.user_id == user_id).delete()
            return

        thread = await ThreadDoc.find_one(ThreadDoc.id == thread_id, ThreadDoc.user_id == user_id)
        if not thread:
            return

        last = max(messages, key=lambda m: m.received_at or datetime.min.replace(tzinfo=timezone.utc))
        thread.subject = last.subject
        thread.folder_id = last.folder_id
        thread.last_message_at = last.received_at
        thread.unread_count = sum(1 for m in messages if not m.is_read)
        thread.total_count = len(messages)
        thread.has_attachments = any(m.has_attachments for m in messages)
        thread.is_flagged = any(m.is_flagged for m in messages)
        thread.participant_emails = list({m.sender.email for m in messages})
        thread.message_ids = [m.id for m in messages]
        await thread.save()
