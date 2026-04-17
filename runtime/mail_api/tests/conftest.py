"""PSense Mail API — Test configuration.

Uses in-memory MongoDB (mongomock_motor) for all tests.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with in-memory database."""
    import os
    os.environ["PSENSE_MAIL__DATABASE__BACKEND"] = "memory"
    os.environ["PSENSE_MAIL__PROVIDER__ACTIVE"] = "memory"
    os.environ["PSENSE_MAIL__AUTH__ENABLED"] = "false"

    # Reset settings singleton
    import config.settings as settings_mod
    settings_mod._settings = None

    from app.main import create_app

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Trigger lifespan startup
        async with app.router.lifespan_context(app):
            yield ac
