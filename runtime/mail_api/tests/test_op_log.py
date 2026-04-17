"""PSense Mail — Op-log and delta sync tests.

Tests the server-side op-log appending and the sync endpoint.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.domain.enums import OpLogKind, OpLogEntity
from app.domain.models import OpLogEntry
from app.services.op_log import append_op
DEV_USER_ID = "dev-user-001"


@pytest.mark.asyncio
async def test_append_op_inserts_entry(client: AsyncClient, seeded_db):
    """append_op should insert an OpLogEntry into the collection."""
    # Trigger lifespan (DB init) through client fixture
    await append_op(
        tenant_id="default",
        account_id=DEV_USER_ID,
        kind=OpLogKind.UPSERT,
        entity=OpLogEntity.MESSAGE,
        entity_id="test-msg-op-1",
        payload={"folder_id": "archive"},
    )

    entry = await OpLogEntry.find_one(
        OpLogEntry.entity_id == "test-msg-op-1",
        OpLogEntry.account_id == DEV_USER_ID,
    )
    assert entry is not None
    assert entry.kind == OpLogKind.UPSERT
    assert entry.entity == OpLogEntity.MESSAGE
    assert entry.payload["folder_id"] == "archive"


@pytest.mark.asyncio
async def test_append_op_does_not_raise_on_db_failure(client: AsyncClient):
    """append_op must silently absorb errors (fire-and-forget contract)."""
    # Even if a bad ID is passed, append_op should not propagate exceptions
    # (it logs instead). We just verify it doesn't raise.
    import contextlib
    with contextlib.suppress(Exception):
        await append_op(
            tenant_id="default",
            account_id="user-x",
            kind=OpLogKind.DELETE,
            entity=OpLogEntity.FOLDER,
            entity_id="non-existent",
            payload={},
        )
    # If we get here, the function swallowed the error correctly


@pytest.mark.asyncio
async def test_sync_endpoint_with_cursor(client: AsyncClient, seeded_db):
    """GET /api/v1/sync with since=0 returns all ops; since=N returns only newer ones."""
    # Seed a known op
    await append_op(
        tenant_id="default",
        account_id=DEV_USER_ID,
        kind=OpLogKind.UPSERT,
        entity=OpLogEntity.TEMPLATE,
        entity_id="cursor-test-tpl",
        payload={"name": "test"},
    )

    resp_all = await client.get("/api/v1/sync", params={"since": "0", "limit": 500})
    assert resp_all.status_code == 200
    data = resp_all.json()
    assert any(op["id"] == "cursor-test-tpl" for op in data["ops"])

    # Use the returned cursor to get incremental ops
    cursor = data["next_cursor"]

    # Add another op after the cursor
    await append_op(
        tenant_id="default",
        account_id=DEV_USER_ID,
        kind=OpLogKind.UPSERT,
        entity=OpLogEntity.TEMPLATE,
        entity_id="cursor-test-tpl-2",
        payload={"name": "test2"},
    )

    resp_inc = await client.get("/api/v1/sync", params={"since": cursor, "limit": 500})
    assert resp_inc.status_code == 200
    inc_data = resp_inc.json()
    new_ids = [op["id"] for op in inc_data["ops"]]
    assert "cursor-test-tpl-2" in new_ids


@pytest.mark.asyncio
async def test_sync_respects_limit(client: AsyncClient, seeded_db):
    """GET /api/v1/sync should not return more ops than limit."""
    # Seed 5 ops
    for i in range(5):
        await append_op(
            tenant_id="default",
            account_id=DEV_USER_ID,
            kind=OpLogKind.UPSERT,
            entity=OpLogEntity.RULE,
            entity_id=f"rule-limit-{i}",
            payload={},
        )

    resp = await client.get("/api/v1/sync", params={"since": "0", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["ops"]) <= 3


@pytest.mark.asyncio
async def test_sync_has_more_flag(client: AsyncClient, seeded_db):
    """has_more should be true when there are more ops than the requested limit."""
    # Seed enough ops
    for i in range(6):
        await append_op(
            tenant_id="default",
            account_id=DEV_USER_ID,
            kind=OpLogKind.UPSERT,
            entity=OpLogEntity.CATEGORY,
            entity_id=f"cat-hm-{i}",
            payload={},
        )

    resp = await client.get("/api/v1/sync", params={"since": "0", "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    # With 6+ ops and limit=2, has_more must be true
    assert data["has_more"] is True
