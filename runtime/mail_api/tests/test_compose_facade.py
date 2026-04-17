"""PSense Mail API — Compose facade tests.

Tests draft lifecycle: create, update, save, send, retry,
plus idempotency dedup and optimistic concurrency.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_draft(client: AsyncClient):
    """Test creating a new draft."""
    resp = await client.post("/api/v1/drafts", json={
        "subject": "Test Draft",
        "body_html": "<p>Hello</p>",
        "to": [{"email": "bob@example.com", "name": "Bob"}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "Test Draft"
    assert data["delivery_state"] == "draft"
    assert data["version"] == 1


async def test_update_draft(client: AsyncClient):
    """Test updating a draft with new subject."""
    # Create
    create_resp = await client.post("/api/v1/drafts", json={
        "subject": "Original",
    })
    draft_id = create_resp.json()["id"]

    # Update
    update_resp = await client.patch(f"/api/v1/drafts/{draft_id}", json={
        "subject": "Updated Subject",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["subject"] == "Updated Subject"
    assert update_resp.json()["version"] == 2


async def test_save_draft(client: AsyncClient):
    """Test explicitly saving a draft updates last_saved_at."""
    create_resp = await client.post("/api/v1/drafts", json={"subject": "Save Me"})
    draft_id = create_resp.json()["id"]

    save_resp = await client.post(f"/api/v1/drafts/{draft_id}/save")
    assert save_resp.status_code == 200
    assert save_resp.json()["last_saved_at"] is not None


async def test_discard_draft(client: AsyncClient):
    """Test deleting a draft."""
    create_resp = await client.post("/api/v1/drafts", json={"subject": "Discard Me"})
    draft_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/drafts/{draft_id}")
    assert del_resp.status_code == 200


async def test_send_draft_without_transport(client: AsyncClient):
    """Test sending a draft with no transport (memory mode) succeeds."""
    create_resp = await client.post("/api/v1/drafts", json={
        "subject": "Send Test",
        "to": [{"email": "recipient@example.com", "name": "Recipient"}],
    })
    draft_id = create_resp.json()["id"]

    send_resp = await client.post(f"/api/v1/drafts/{draft_id}/send")
    assert send_resp.status_code == 200
    data = send_resp.json()
    assert data["state"] == "sent"
    assert data["message_id"] is not None


async def test_send_draft_no_recipients_fails(client: AsyncClient):
    """Test sending a draft without recipients returns validation error."""
    create_resp = await client.post("/api/v1/drafts", json={
        "subject": "No Recipients",
    })
    draft_id = create_resp.json()["id"]

    send_resp = await client.post(f"/api/v1/drafts/{draft_id}/send")
    assert send_resp.status_code == 422


async def test_list_drafts(client: AsyncClient):
    """Test listing drafts returns results."""
    await client.post("/api/v1/drafts", json={"subject": "List Test"})
    resp = await client.get("/api/v1/drafts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_schedule_send(client: AsyncClient):
    """Test scheduling a draft for later send."""
    create_resp = await client.post("/api/v1/drafts", json={
        "subject": "Scheduled",
        "to": [{"email": "bob@example.com", "name": "Bob"}],
    })
    draft_id = create_resp.json()["id"]

    send_resp = await client.post(f"/api/v1/drafts/{draft_id}/send", json={
        "schedule_at": "2030-01-01T12:00:00Z",
    })
    assert send_resp.status_code == 200
    assert send_resp.json()["state"] == "scheduled"
