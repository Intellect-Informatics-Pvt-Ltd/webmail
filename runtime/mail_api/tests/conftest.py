"""PSense Mail API — Test configuration.

Uses in-memory MongoDB (mongomock_motor) for all tests.
Provides shared fixtures for user, folders, messages, and drafts.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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
    os.environ["PSENSE_MAIL__WORKERS__ENABLED"] = "false"

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


# ── Shared constants ──────────────────────────────────────────────────────────

DEV_USER_ID = "dev-user-001"
DEV_USER_EMAIL = "avery@psense.ai"
DEV_USER_NAME = "Avery Chen"


# ── Facade fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seeded_db(client: AsyncClient):
    """Ensure the database is seeded and return the client.
    
    The lifespan in conftest already seeds in memory mode, so this is
    mostly a semantic marker for tests that need seed data.
    """
    return client


@pytest_asyncio.fixture
async def mail_facade():
    """Create a MailFacade instance for direct testing."""
    from app.services.mail_facade import MailFacade
    return MailFacade()


@pytest_asyncio.fixture
async def compose_facade():
    """Create a ComposeFacade instance for direct testing."""
    from app.services.compose_facade import ComposeFacade
    return ComposeFacade(transport=None)


@pytest_asyncio.fixture
async def search_facade():
    """Create a SearchFacade with memory adapter for direct testing."""
    from app.adapters.search.memory import MemorySearchAdapter
    from app.services.search_facade import SearchFacade
    return SearchFacade(search_adapter=MemorySearchAdapter())


@pytest_asyncio.fixture
async def rules_facade():
    """Create a RulesFacade instance for direct testing."""
    from app.services.rules_facade import RulesFacade
    return RulesFacade()
