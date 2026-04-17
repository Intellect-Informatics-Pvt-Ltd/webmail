"""PSense Mail — MongoDB connection manager.

Provides async Motor client + Beanie ODM initialisation.

Usage:
    - Production: connects to a real MongoDB via `database.mongo.uri`
    - Dev/test:   uses mongomock_motor in-memory backend when
                  `database.backend == "memory"`
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.domain.models import ALL_DOCUMENTS

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)

# Module-level client reference — set during lifespan init.
_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]


async def init_mongo(settings: "Settings") -> AsyncIOMotorClient:  # type: ignore[type-arg]
    """Initialise MongoDB client and Beanie ODM.

    Returns the Motor client (needed for shutdown).
    """
    global _client

    if settings.database.backend == "memory":
        logger.info("Using in-memory MongoDB (mongomock_motor)")
        try:
            from mongomock_motor import AsyncMongoMockClient
            _client = AsyncMongoMockClient()
        except ImportError as exc:
            raise RuntimeError(
                "mongomock-motor is required for in-memory mode. "
                "Install it: pip install mongomock-motor"
            ) from exc
    else:
        mongo_cfg = settings.database.mongo
        logger.info("Connecting to MongoDB at %s", mongo_cfg.uri)
        _client = AsyncIOMotorClient(
            mongo_cfg.uri,
            minPoolSize=mongo_cfg.min_pool_size,
            maxPoolSize=mongo_cfg.max_pool_size,
        )

    db_name = settings.database.mongo.db_name
    database = _client[db_name]

    await init_beanie(database=database, document_models=ALL_DOCUMENTS)
    logger.info("Beanie ODM initialised — database: %s, collections: %d", db_name, len(ALL_DOCUMENTS))

    return _client


async def close_mongo() -> None:
    """Close the MongoDB client connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


def get_client() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    """Get the active Motor client. Raises if not initialised."""
    if _client is None:
        raise RuntimeError("MongoDB client not initialised — call init_mongo() first")
    return _client
