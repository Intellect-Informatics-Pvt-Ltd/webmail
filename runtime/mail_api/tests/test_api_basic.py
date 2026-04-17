"""PSense Mail API — Basic API tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health_check(client: AsyncClient):
    """Test health endpoint returns 200 OK and covers adapters."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded", "down")
    assert "adapters" in data
    # memory provider in test env
    adapter_names = [a["name"] for a in data["adapters"]]
    assert any("transport" in n.lower() for n in adapter_names)


async def test_admin_diagnostics(client: AsyncClient):
    """Test diagnostics endpoint to verify DB memory seeder ran."""
    response = await client.get("/api/v1/admin/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["message_count"] > 0
    assert data["folder_count"] > 0
    
    
async def test_openapi_schema(client: AsyncClient):
    """Test OpenAPI schema generation doesn't crash."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "/api/v1/health" in data["paths"]
    assert "/api/v1/messages" in data["paths"]
