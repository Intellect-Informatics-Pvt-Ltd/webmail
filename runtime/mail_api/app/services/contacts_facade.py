"""PSense Mail — ContactsFacade service.

CRUD operations for the address book. Contacts are scoped per user.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.errors import NotFoundError
from app.domain.models import ContactDoc
from app.domain.enums import OpLogEntity, OpLogKind
from app.services.op_log import append_op

logger = logging.getLogger(__name__)


class ContactsFacade:
    """Contacts CRUD facade."""

    async def list_contacts(
        self, user_id: str, query: str | None = None,
        cursor: str | None = None, limit: int = 100,
    ) -> dict[str, Any]:
        """List contacts with optional search and cursor pagination."""
        filters: dict[str, Any] = {"user_id": user_id, "deleted_at": None}

        if query:
            filters["$or"] = [
                {"display_name": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}},
                {"first_name": {"$regex": query, "$options": "i"}},
                {"last_name": {"$regex": query, "$options": "i"}},
                {"company": {"$regex": query, "$options": "i"}},
            ]

        if cursor:
            filters["_id"] = {"$gt": cursor}

        docs = await ContactDoc.find(filters).sort(
            [("display_name", 1)]
        ).limit(limit + 1).to_list()

        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]

        next_cursor = docs[-1].id if has_more and docs else None
        return {
            "items": [d.model_dump(by_alias=True) for d in docs],
            "next_cursor": next_cursor,
            "total_estimate": await ContactDoc.find({"user_id": user_id, "deleted_at": None}).count(),
        }

    async def get_contact(self, user_id: str, contact_id: str) -> ContactDoc:
        doc = await ContactDoc.find_one(ContactDoc.id == contact_id, ContactDoc.user_id == user_id)
        if not doc or doc.deleted_at:
            raise NotFoundError("Contact", contact_id)
        return doc

    async def create_contact(
        self, user_id: str, data: dict[str, Any],
        tenant_id: str = "default", account_id: str = "",
    ) -> ContactDoc:
        doc = ContactDoc(
            user_id=user_id,
            tenant_id=tenant_id,
            account_id=account_id or user_id,
            **{k: v for k, v in data.items() if k not in ("user_id", "tenant_id", "account_id")},
        )
        await doc.insert()
        await append_op(
            tenant_id=tenant_id, account_id=account_id or user_id,
            kind=OpLogKind.UPSERT, entity=OpLogEntity.MESSAGE,  # reuse entity for now
            entity_id=doc.id, payload=doc.model_dump(mode="json"),
        )
        return doc

    async def update_contact(
        self, user_id: str, contact_id: str, patch: dict[str, Any],
    ) -> ContactDoc:
        doc = await self.get_contact(user_id, contact_id)
        for key, val in patch.items():
            if val is not None and hasattr(doc, key) and key not in ("id", "user_id", "tenant_id"):
                setattr(doc, key, val)
        doc.updated_at = datetime.now(timezone.utc)
        doc.version += 1
        await doc.save()
        return doc

    async def delete_contact(self, user_id: str, contact_id: str) -> None:
        doc = await self.get_contact(user_id, contact_id)
        doc.deleted_at = datetime.now(timezone.utc)
        await doc.save()

    async def merge_contacts(
        self, user_id: str, primary_id: str, secondary_ids: list[str],
    ) -> ContactDoc:
        """Merge secondary contacts into primary, then soft-delete secondaries."""
        primary = await self.get_contact(user_id, primary_id)
        for sid in secondary_ids:
            secondary = await self.get_contact(user_id, sid)
            # Merge non-empty fields from secondary into primary
            for field in ("phone", "company", "job_title", "notes", "avatar_url"):
                if not getattr(primary, field) and getattr(secondary, field):
                    setattr(primary, field, getattr(secondary, field))
            for group in secondary.groups:
                if group not in primary.groups:
                    primary.groups.append(group)
            secondary.deleted_at = datetime.now(timezone.utc)
            await secondary.save()

        primary.updated_at = datetime.now(timezone.utc)
        primary.version += 1
        await primary.save()
        return primary
