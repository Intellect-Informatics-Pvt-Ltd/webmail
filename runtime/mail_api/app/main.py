"""PSense Mail — FastAPI application factory.

Creates and configures the FastAPI application with:
  - Lifespan management (MongoDB init/close, seed, adapter registry)
  - Middleware stack (CORS, correlation, auth, error handler)
  - Router registration
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.registry import AdapterRegistry
from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Module-level references — set during lifespan
_registry: AdapterRegistry | None = None
_settings: Settings | None = None


def get_registry() -> AdapterRegistry:
    """Get the active adapter registry."""
    if _registry is None:
        raise RuntimeError("App not initialised — adapter registry is None")
    return _registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — init and teardown."""
    global _registry, _settings

    settings = get_settings()
    _settings = settings

    # Configure logging
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    logger.info("Starting PSense Mail API v%s", settings.app.version)
    logger.info("Database backend: %s", settings.database.backend)
    logger.info("Mail provider: %s", settings.provider.active)
    logger.info("File storage: %s", settings.file_storage.backend)

    # Init MongoDB + Beanie
    from app.adapters.db.mongo import init_mongo, close_mongo

    await init_mongo(settings)

    # Init adapter registry
    _registry = AdapterRegistry(settings)

    # Seed demo data in memory mode
    if settings.database.backend == "memory" and settings.database.memory.seed_on_start:
        from app.seed.demo_data import seed_demo_data
        await seed_demo_data(settings.auth.dev_user_id)

    # Start background workers
    from app.workers.manager import WorkerManager
    worker_manager = WorkerManager(settings, _registry)
    worker_manager.start_all()

    logger.info("PSense Mail API ready")

    yield  # Application runs

    # Teardown
    logger.info("Shutting down PSense Mail API")
    worker_manager.stop_all()
    await close_mongo()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="PSense Mail — Configuration-driven enterprise mail API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost first) ──────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handler (catches domain exceptions from services)
    from app.middleware.error_handler import ErrorHandlerMiddleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Idempotency cache (read-through/write-through for mutating requests)
    from app.middleware.idempotency import IdempotencyMiddleware
    app.add_middleware(IdempotencyMiddleware)

    # Correlation ID
    from app.middleware.correlation import CorrelationMiddleware
    app.add_middleware(CorrelationMiddleware, header_name=settings.logging.correlation_header)

    # Authentication
    from app.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # ── Routers ──────────────────────────────────────────────────────────

    from app.api.routers.admin import router as admin_router
    app.include_router(admin_router)

    from app.api.routers.messages import router as messages_router
    from app.api.routers.threads import router as threads_router
    from app.api.routers.mailbox import router as mailbox_router
    from app.api.routers.drafts import router as drafts_router
    from app.api.routers.search import router as search_router
    from app.api.routers.rules import router as rules_router
    from app.api.routers.templates import router as templates_router
    from app.api.routers.signatures import router as signatures_router
    from app.api.routers.categories import router as categories_router
    from app.api.routers.preferences import router as preferences_router
    from app.api.routers.saved_searches import router as saved_searches_router
    from app.api.routers.attachments import router as attachments_router
    from app.api.routers.sync import router as sync_router

    app.include_router(messages_router)
    app.include_router(threads_router)
    app.include_router(mailbox_router)
    app.include_router(drafts_router)
    app.include_router(search_router)
    app.include_router(rules_router)
    app.include_router(templates_router)
    app.include_router(signatures_router)
    app.include_router(categories_router)
    app.include_router(preferences_router)
    app.include_router(saved_searches_router)
    app.include_router(attachments_router)
    app.include_router(sync_router)

    return app


# ── Uvicorn entry point ─────────────────────────────────────────────────────

app = create_app()
