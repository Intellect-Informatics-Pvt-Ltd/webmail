"""PSense Mail — Delta sync router.

GET /api/v1/sync?since=<cursor>&account_id=<id>&limit=500

Streams op-log entries to clients for offline sync (Tier 4).

Cursor format
-------------
The cursor is an opaque base64-url encoded string representing the last
consumed op-log `seq` value. Clients store it per account_id in Dexie
(sync_cursors table) and send it on every poll.

A cursor value of "0" or empty starts from the beginning (full sync).

Response shape
--------------
{
  "next_cursor": "<opaque>",
  "ops": [
    {
      "seq": 120341,
      "kind": "upsert",
      "entity": "message",
      "id": "...",
      "payload": { ... }   // full current projection
    }
  ],
  "has_more": true
}
"""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_account_id, get_current_user, get_tenant_id
from app.domain.models import OpLogEntry
from app.middleware.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["sync"])

MAX_LIMIT = 500


def _decode_cursor(cursor: str | None) -> int:
    """Decode opaque cursor to seq integer."""
    if not cursor or cursor == "0":
        return 0
    try:
        decoded = base64.urlsafe_b64decode(cursor + "==").decode("utf-8")
        return int(decoded)
    except Exception:
        return 0


def _encode_cursor(seq: int) -> str:
    """Encode seq integer to opaque cursor string."""
    return base64.urlsafe_b64encode(str(seq).encode("utf-8")).rstrip(b"=").decode("utf-8")


@router.get("/sync")
async def delta_sync(
    since: str | None = Query(default=None, description="Opaque cursor from previous response"),
    limit: int = Query(default=200, ge=1, le=MAX_LIMIT),
    user: AuthenticatedUser = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    account_id: str = Depends(get_account_id),
) -> dict:
    """Return op-log entries since the given cursor for offline sync.

    Clients MUST process ops in seq order.
    Deleted entities have kind="delete" and payload={"deleted_at": "..."}.
    """
    since_seq = _decode_cursor(since)

    # Fetch one extra to determine has_more
    entries = await OpLogEntry.find(
        OpLogEntry.tenant_id == tenant_id,
        OpLogEntry.account_id == account_id,
        OpLogEntry.seq > since_seq,
    ).sort("+seq").limit(limit + 1).to_list()

    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]

    ops = [
        {
            "seq": entry.seq,
            "kind": entry.kind,
            "entity": entry.entity,
            "id": entry.entity_id,
            "payload": entry.payload,
        }
        for entry in entries
    ]

    next_cursor = _encode_cursor(entries[-1].seq) if entries else (since or "0")

    return {
        "next_cursor": next_cursor,
        "ops": ops,
        "has_more": has_more,
    }
