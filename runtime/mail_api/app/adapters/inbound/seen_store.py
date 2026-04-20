"""PSense Mail — Seen-ID deduplication store for POP3 adapter.

Tracks provider message UIDs that have already been fetched, preventing
duplicate ingestion across poller cycles. Two backends:
  - MemorySeenStore: in-memory set (default, lost on restart)
  - MongoSeenStore: persistent MongoDB collection (when database.backend == "mongo")
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class SeenStore(Protocol):
    """Protocol for provider message UID deduplication."""

    async def contains(self, uid: str) -> bool:
        """Check if a UID has already been seen."""
        ...

    async def contains_many(self, uids: list[str]) -> set[str]:
        """Return the subset of UIDs that have already been seen."""
        ...

    async def add_many(self, uids: list[str]) -> None:
        """Mark UIDs as seen."""
        ...

    async def remove_many(self, uids: list[str]) -> None:
        """Remove UIDs from the seen set (after successful acknowledge)."""
        ...


class MemorySeenStore:
    """In-memory seen store — fast but lost on process restart."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def contains(self, uid: str) -> bool:
        return uid in self._seen

    async def contains_many(self, uids: list[str]) -> set[str]:
        return self._seen & set(uids)

    async def add_many(self, uids: list[str]) -> None:
        self._seen.update(uids)

    async def remove_many(self, uids: list[str]) -> None:
        self._seen -= set(uids)


class MongoSeenStore:
    """MongoDB-backed seen store — survives process restarts.

    Uses the `pop3_seen_ids` collection with documents:
        { _id: <uid>, user_id: str, seen_at: datetime }
    """

    def __init__(self, user_id: str = "default") -> None:
        self._user_id = user_id
        self._collection_name = "pop3_seen_ids"

    def _get_collection(self):
        """Lazily get the motor collection via Beanie's database."""
        from beanie import Document
        # Access the underlying motor database from Beanie
        db = Document.get_motor_collection().database
        return db[self._collection_name]

    async def contains(self, uid: str) -> bool:
        coll = self._get_collection()
        doc = await coll.find_one({"_id": uid, "user_id": self._user_id})
        return doc is not None

    async def contains_many(self, uids: list[str]) -> set[str]:
        if not uids:
            return set()
        coll = self._get_collection()
        cursor = coll.find(
            {"_id": {"$in": uids}, "user_id": self._user_id},
            projection={"_id": 1},
        )
        found: set[str] = set()
        async for doc in cursor:
            found.add(doc["_id"])
        return found

    async def add_many(self, uids: list[str]) -> None:
        if not uids:
            return
        coll = self._get_collection()
        now = datetime.now(timezone.utc)
        # Use unordered bulk insert, ignore duplicates
        from pymongo.errors import BulkWriteError
        docs = [{"_id": uid, "user_id": self._user_id, "seen_at": now} for uid in uids]
        try:
            await coll.insert_many(docs, ordered=False)
        except BulkWriteError:
            # Some were already present — that's fine
            pass

    async def remove_many(self, uids: list[str]) -> None:
        if not uids:
            return
        coll = self._get_collection()
        await coll.delete_many({"_id": {"$in": uids}, "user_id": self._user_id})


def create_seen_store(database_backend: str, user_id: str = "default") -> SeenStore:
    """Factory function to create the appropriate seen store."""
    if database_backend == "mongo":
        logger.info("Using MongoDB-backed seen store for POP3 deduplication")
        return MongoSeenStore(user_id=user_id)
    else:
        logger.info("Using in-memory seen store for POP3 deduplication")
        return MemorySeenStore()
