"""PSense Mail API — Mail facade tests.

Tests message listing, detail, bulk actions, folder CRUD,
optimistic concurrency, and idempotency.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_messages(client: AsyncClient):
    """Test listing messages from the injected seed data."""
    response = await client.get("/api/v1/messages")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["total_estimate"] > 0

    first_msg = data["items"][0]
    assert "id" in first_msg
    assert "subject" in first_msg


async def test_list_messages_with_filters(client: AsyncClient):
    """Test listing messages with query filters."""
    resp = await client.get("/api/v1/messages?folder_id=inbox&limit=5")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 5


async def test_get_message(client: AsyncClient):
    """Test getting a specific message marks it as read."""
    list_resp = await client.get("/api/v1/messages?folder_id=inbox&is_read=false")
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No unread messages found to test")

    msg_id = items[0]["id"]

    detail_resp = await client.get(f"/api/v1/messages/{msg_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["is_read"] is True


async def test_get_message_not_found(client: AsyncClient):
    """Test getting a nonexistent message returns 404."""
    resp = await client.get("/api/v1/messages/nonexistent-id-12345")
    assert resp.status_code == 404


async def test_folders(client: AsyncClient):
    """Test folder listing and counts."""
    response = await client.get("/api/v1/folders")
    assert response.status_code == 200
    folders = response.json()
    assert any(f["id"] == "inbox" for f in folders)

    counts_resp = await client.get("/api/v1/folders/counts")
    counts = counts_resp.json()
    assert "inbox" in counts["counts"]


async def test_create_and_delete_folder(client: AsyncClient):
    """Test creating and deleting a custom folder."""
    create_resp = await client.post("/api/v1/folders", json={"name": "Test Folder"})
    assert create_resp.status_code == 201
    folder_id = create_resp.json()["id"]
    assert create_resp.json()["kind"] == "custom"

    del_resp = await client.delete(f"/api/v1/folders/{folder_id}")
    assert del_resp.status_code == 200


async def test_rename_folder(client: AsyncClient):
    """Test renaming a custom folder."""
    create_resp = await client.post("/api/v1/folders", json={"name": "Rename Me"})
    folder_id = create_resp.json()["id"]

    rename_resp = await client.patch(f"/api/v1/folders/{folder_id}", json={"name": "Renamed"})
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "Renamed"


async def test_cannot_rename_system_folder(client: AsyncClient):
    """Test that renaming a system folder fails."""
    rename_resp = await client.patch("/api/v1/folders/inbox", json={"name": "Not Inbox"})
    assert rename_resp.status_code == 422


async def test_bulk_actions(client: AsyncClient):
    """Test bulk flagging messages."""
    list_resp = await client.get("/api/v1/messages?limit=2")
    items = list_resp.json()["items"]
    msg_ids = [m["id"] for m in items]

    action_resp = await client.post(
        "/api/v1/messages/actions",
        json={"message_ids": msg_ids, "action": "flag"}
    )
    assert action_resp.status_code == 200
    assert len(action_resp.json()["succeeded_ids"]) == len(msg_ids)

    detail_resp = await client.get(f"/api/v1/messages/{msg_ids[0]}")
    assert detail_resp.json()["is_flagged"] is True


async def test_bulk_action_move(client: AsyncClient):
    """Test moving messages to a folder."""
    list_resp = await client.get("/api/v1/messages?limit=1")
    msg_id = list_resp.json()["items"][0]["id"]

    resp = await client.post("/api/v1/messages/actions", json={
        "message_ids": [msg_id],
        "action": "move",
        "destination_folder_id": "archive",
    })
    assert resp.status_code == 200
    assert msg_id in resp.json()["succeeded_ids"]


async def test_bulk_action_idempotency(client: AsyncClient):
    """Test that idempotency key prevents duplicate action execution."""
    list_resp = await client.get("/api/v1/messages?limit=1")
    msg_id = list_resp.json()["items"][0]["id"]

    idem_key = "test-idempotency-key-001"

    # First call
    resp1 = await client.post("/api/v1/messages/actions", json={
        "message_ids": [msg_id],
        "action": "flag",
        "idempotency_key": idem_key,
    })
    assert resp1.status_code == 200

    # Second call with same key should return cached result
    resp2 = await client.post("/api/v1/messages/actions", json={
        "message_ids": [msg_id],
        "action": "unflag",  # different action but same key
        "idempotency_key": idem_key,
    })
    assert resp2.status_code == 200
    # Should return the same result as the first call (flag, not unflag)
    assert resp2.json()["succeeded_ids"] == resp1.json()["succeeded_ids"]


async def test_bulk_action_concurrency_check(client: AsyncClient):
    """Test that expected_version mismatch is reported."""
    list_resp = await client.get("/api/v1/messages?limit=1")
    msg_id = list_resp.json()["items"][0]["id"]

    # Use a very wrong version
    resp = await client.post("/api/v1/messages/actions", json={
        "message_ids": [msg_id],
        "action": "flag",
        "expected_version": 999,
    })
    assert resp.status_code == 200
    # The msg_id should be in failed due to version mismatch
    assert msg_id in resp.json()["failed"]


async def test_virtual_folder_flagged(client: AsyncClient):
    """Test listing messages from the virtual 'flagged' folder."""
    # First flag a message
    list_resp = await client.get("/api/v1/messages?limit=1")
    msg_id = list_resp.json()["items"][0]["id"]
    await client.post("/api/v1/messages/actions", json={
        "message_ids": [msg_id], "action": "flag",
    })

    # Now list flagged
    flagged_resp = await client.get("/api/v1/messages?folder_id=flagged")
    assert flagged_resp.status_code == 200
    assert any(m["id"] == msg_id for m in flagged_resp.json()["items"])
