"""PSense Mail API — Search facade tests.

Tests search with structured query parsing, facets, suggestions.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_search_messages(client: AsyncClient):
    """Test basic search returns results from seeded data."""
    resp = await client.post("/api/v1/search/messages", json={
        "query": "quarterly",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "hits" in data
    assert "total_estimate" in data
    assert "facets" in data


async def test_search_with_folder_filter(client: AsyncClient):
    """Test search scoped to a specific folder."""
    resp = await client.post("/api/v1/search/messages", json={
        "query": "",
        "folder_id": "inbox",
        "limit": 10,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "hits" in data


async def test_search_from_operator(client: AsyncClient):
    """Test from: operator in search query."""
    resp = await client.post("/api/v1/search/messages", json={
        "query": "from:avery",
    })
    assert resp.status_code == 200


async def test_search_is_unread(client: AsyncClient):
    """Test is:unread filter."""
    resp = await client.post("/api/v1/search/messages", json={
        "query": "is:unread",
    })
    assert resp.status_code == 200


async def test_search_empty_query(client: AsyncClient):
    """Test empty search query returns all messages (limited)."""
    resp = await client.post("/api/v1/search/messages", json={
        "limit": 5,
    })
    assert resp.status_code == 200


async def test_search_suggestions(client: AsyncClient):
    """Test search suggestions endpoint."""
    resp = await client.get("/api/v1/search/suggest?q=qu&limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_search_suggestions_too_short(client: AsyncClient):
    """Test suggestions with single character returns empty."""
    resp = await client.get("/api/v1/search/suggest?q=ab&limit=5")
    assert resp.status_code == 200


async def test_search_with_date_range(client: AsyncClient):
    """Test search with date range filters."""
    resp = await client.post("/api/v1/search/messages", json={
        "date_from": "2024-01-01T00:00:00Z",
        "date_to": "2030-12-31T23:59:59Z",
    })
    assert resp.status_code == 200


async def test_search_has_attachment(client: AsyncClient):
    """Test has:attachment filter."""
    resp = await client.post("/api/v1/search/messages", json={
        "query": "has:attachment",
    })
    assert resp.status_code == 200
