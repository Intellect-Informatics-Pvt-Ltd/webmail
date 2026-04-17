"""PSense Mail API — Rules facade tests.

Tests rule CRUD and evaluation.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_rule(client: AsyncClient):
    """Test creating a mail rule."""
    resp = await client.post("/api/v1/rules", json={
        "name": "Test Rule",
        "enabled": True,
        "conditions": [
            {"field": "sender", "op": "contains", "value": "newsletter"}
        ],
        "actions": [
            {"type": "move", "folder_id": "archive"}
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Rule"
    assert data["enabled"] is True
    assert len(data["conditions"]) == 1
    assert len(data["actions"]) == 1


async def test_list_rules(client: AsyncClient):
    """Test listing rules returns seeded rules."""
    resp = await client.get("/api/v1/rules")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_update_rule(client: AsyncClient):
    """Test updating a rule's name and enabled state."""
    # Create first
    create_resp = await client.post("/api/v1/rules", json={
        "name": "Update Me",
        "conditions": [{"field": "subject", "op": "contains", "value": "test"}],
        "actions": [{"type": "archive"}],
    })
    rule_id = create_resp.json()["_id"]

    # Update
    update_resp = await client.put(f"/api/v1/rules/{rule_id}", json={
        "name": "Updated Rule",
        "enabled": False,
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Rule"
    assert update_resp.json()["enabled"] is False


async def test_delete_rule(client: AsyncClient):
    """Test deleting a rule."""
    create_resp = await client.post("/api/v1/rules", json={
        "name": "Delete Me",
        "conditions": [{"field": "sender", "op": "equals", "value": "spam@example.com"}],
        "actions": [{"type": "delete"}],
    })
    rule_id = create_resp.json()["_id"]

    del_resp = await client.delete(f"/api/v1/rules/{rule_id}")
    assert del_resp.status_code == 200
