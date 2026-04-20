"""Migration 0003 — Backfill account_id from user_id.

For all documents where account_id is empty, sets account_id = user_id.
"""
DESCRIPTION = "Backfill account_id from user_id on existing documents"


async def up() -> None:
    from app.domain.models import (
        MessageDoc, ThreadDoc, FolderDoc, DraftDoc,
        CategoryDoc, RuleDoc, TemplateDoc, SignatureDoc,
        SavedSearchDoc, ContactDoc, CalendarEventDoc,
    )
    collections = [
        MessageDoc, ThreadDoc, FolderDoc, DraftDoc,
        CategoryDoc, RuleDoc, TemplateDoc, SignatureDoc,
        SavedSearchDoc, ContactDoc, CalendarEventDoc,
    ]
    for model in collections:
        coll = model.get_motor_collection()
        result = await coll.update_many(
            {"$or": [{"account_id": ""}, {"account_id": {"$exists": False}}]},
            [{"$set": {"account_id": "$user_id"}}],
        )
        if result.modified_count:
            print(f"    {model.Settings.name}: backfilled {result.modified_count} docs")
