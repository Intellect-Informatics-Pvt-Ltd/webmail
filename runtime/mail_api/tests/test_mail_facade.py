"""PSense Mail API — Mail facade tests."""
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


async def test_get_message(client: AsyncClient):
    """Test getting a specific message marks it as read."""
    # First get list to find an ID
    list_resp = await client.get("/api/v1/messages?folder_id=inbox&is_read=false")
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No unread messages found to test")
        
    msg_id = items[0]["id"]
    
    # Get message detail
    detail_resp = await client.get(f"/api/v1/messages/{msg_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["is_read"] is True


async def test_folders(client: AsyncClient):
    """Test folder listing and counts."""
    response = await client.get("/api/v1/folders")
    assert response.status_code == 200
    folders = response.json()
    assert any(f["id"] == "inbox" for f in folders)
    
    counts_resp = await client.get("/api/v1/folders/counts")
    counts = counts_resp.json()
    assert "inbox" in counts["counts"]


async def test_bulk_actions(client: AsyncClient):
    """Test bulk flagging messages."""
    list_resp = await client.get("/api/v1/messages?limit=2")
    items = list_resp.json()["items"]
    msg_ids = [m["id"] for m in items]
    
    # Flag messages
    action_resp = await client.post(
        "/api/v1/messages/actions",
        json={"message_ids": msg_ids, "action": "flag"}
    )
    assert action_resp.status_code == 200
    assert len(action_resp.json()["succeeded_ids"]) == len(msg_ids)
    
    # Verify flagged
    detail_resp = await client.get(f"/api/v1/messages/{msg_ids[0]}")
    assert detail_resp.json()["is_flagged"] is True
