"""PSense Mail — GDPR Data Export service.

Exports all user data in a structured JSON format for GDPR compliance.
Includes messages, contacts, drafts, preferences, and audit trail.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.models import (
    AccountDoc,
    AuditLogDoc,
    CalendarEventDoc,
    CategoryDoc,
    ContactDoc,
    DraftDoc,
    FolderDoc,
    MessageDoc,
    PreferencesDoc,
    RuleDoc,
    SavedSearchDoc,
    SignatureDoc,
    TemplateDoc,
    ThreadDoc,
    UserDoc,
)

logger = logging.getLogger(__name__)


class GDPRExportService:
    """Export all user data for GDPR compliance."""

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        """Export all data for a user. Returns structured JSON."""
        logger.info("Starting GDPR data export for user %s", user_id)
        start = datetime.now(timezone.utc)

        export: dict[str, Any] = {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": start.isoformat(),
                "format_version": "1.0",
            },
        }

        # User profile
        user = await UserDoc.find_one(UserDoc.id == user_id)
        if user:
            export["profile"] = user.model_dump(mode="json")

        # Accounts
        accounts = await AccountDoc.find(AccountDoc.owner_user_id == user_id).to_list()
        export["accounts"] = [a.model_dump(mode="json", exclude={"provider_meta", "provider_meta_enc"}) for a in accounts]

        # Messages (exclude body_html for size, include metadata)
        messages = await MessageDoc.find(MessageDoc.user_id == user_id).to_list()
        export["messages"] = [
            m.model_dump(mode="json", exclude={"body_html"}) for m in messages
        ]
        export["message_count"] = len(messages)

        # Threads
        threads = await ThreadDoc.find(ThreadDoc.user_id == user_id).to_list()
        export["threads"] = [t.model_dump(mode="json") for t in threads]

        # Drafts
        drafts = await DraftDoc.find(DraftDoc.user_id == user_id).to_list()
        export["drafts"] = [d.model_dump(mode="json") for d in drafts]

        # Folders
        folders = await FolderDoc.find(FolderDoc.user_id == user_id).to_list()
        export["folders"] = [f.model_dump(mode="json") for f in folders]

        # Categories
        categories = await CategoryDoc.find(CategoryDoc.user_id == user_id).to_list()
        export["categories"] = [c.model_dump(mode="json") for c in categories]

        # Rules
        rules = await RuleDoc.find(RuleDoc.user_id == user_id).to_list()
        export["rules"] = [r.model_dump(mode="json") for r in rules]

        # Templates
        templates = await TemplateDoc.find(TemplateDoc.user_id == user_id).to_list()
        export["templates"] = [t.model_dump(mode="json") for t in templates]

        # Signatures
        signatures = await SignatureDoc.find(SignatureDoc.user_id == user_id).to_list()
        export["signatures"] = [s.model_dump(mode="json") for s in signatures]

        # Preferences
        prefs = await PreferencesDoc.find_one(PreferencesDoc.id == user_id)
        if prefs:
            export["preferences"] = prefs.model_dump(mode="json")

        # Saved searches
        searches = await SavedSearchDoc.find(SavedSearchDoc.user_id == user_id).to_list()
        export["saved_searches"] = [s.model_dump(mode="json") for s in searches]

        # Contacts
        contacts = await ContactDoc.find(ContactDoc.user_id == user_id).to_list()
        export["contacts"] = [c.model_dump(mode="json") for c in contacts]

        # Calendar events
        events = await CalendarEventDoc.find(CalendarEventDoc.user_id == user_id).to_list()
        export["calendar_events"] = [e.model_dump(mode="json") for e in events]

        # Audit log (last 90 days)
        audit = await AuditLogDoc.find(AuditLogDoc.user_id == user_id).sort(
            [("created_at", -1)]
        ).limit(1000).to_list()
        export["audit_log"] = [a.model_dump(mode="json") for a in audit]

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        export["export_metadata"]["duration_seconds"] = duration
        logger.info("GDPR export completed for user %s in %.2fs", user_id, duration)

        return export

    async def delete_user_data(self, user_id: str) -> dict[str, int]:
        """Delete all data for a user (right to erasure). Returns counts of deleted items."""
        logger.warning("Starting GDPR data deletion for user %s", user_id)
        counts: dict[str, int] = {}

        for model, name in [
            (MessageDoc, "messages"),
            (ThreadDoc, "threads"),
            (DraftDoc, "drafts"),
            (FolderDoc, "folders"),
            (CategoryDoc, "categories"),
            (RuleDoc, "rules"),
            (TemplateDoc, "templates"),
            (SignatureDoc, "signatures"),
            (SavedSearchDoc, "saved_searches"),
            (ContactDoc, "contacts"),
            (CalendarEventDoc, "calendar_events"),
        ]:
            docs = await model.find(model.user_id == user_id).to_list()
            for doc in docs:
                await doc.delete()
            counts[name] = len(docs)

        # Delete preferences
        prefs = await PreferencesDoc.find_one(PreferencesDoc.id == user_id)
        if prefs:
            await prefs.delete()
            counts["preferences"] = 1

        # Delete user profile
        user = await UserDoc.find_one(UserDoc.id == user_id)
        if user:
            await user.delete()
            counts["user_profile"] = 1

        logger.warning("GDPR deletion completed for user %s: %s", user_id, counts)
        return counts
