"""PSense Mail — Accounts (POP3 settings & status) API router.

Provides endpoints for reading/writing POP3 configuration, testing
connectivity, triggering immediate syncs, and querying poller status.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["accounts"])


# ── Request/Response models ───────────────────────────────────────────────────


class Pop3SettingsResponse(BaseModel):
    """POP3 config returned to client (password excluded)."""
    host: str
    port: int
    username: str
    tls_mode: str
    connect_timeout_seconds: int
    max_messages_per_poll: int


class Pop3SettingsPatchRequest(BaseModel):
    """Partial update to POP3 settings."""
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    tls_mode: str | None = None
    connect_timeout_seconds: int | None = None
    max_messages_per_poll: int | None = None


class Pop3TestRequest(BaseModel):
    """Optional override credentials for connection test."""
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    tls_mode: str | None = None


class Pop3StatusResponse(BaseModel):
    last_poll_at: str | None = None
    last_poll_status: str = "never"
    last_error: str | None = None
    messages_last_cycle: int = 0
    is_polling: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_settings():
    from config.settings import get_settings
    return get_settings()


def _get_poller():
    """Get the running InboundPollerWorker instance (if any)."""
    from app.main import _inbound_poller
    return _inbound_poller


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/accounts/pop3", response_model=Pop3SettingsResponse)
async def get_pop3_settings(
    user: AuthenticatedUser = Depends(get_current_user),
) -> Pop3SettingsResponse:
    """Return current POP3 configuration (password excluded)."""
    cfg = _get_settings().provider.pop3
    return Pop3SettingsResponse(
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        tls_mode=cfg.tls_mode,
        connect_timeout_seconds=cfg.connect_timeout_seconds,
        max_messages_per_poll=cfg.max_messages_per_poll,
    )


@router.patch("/accounts/pop3", response_model=Pop3SettingsResponse)
async def update_pop3_settings(
    body: Pop3SettingsPatchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Pop3SettingsResponse:
    """Update POP3 settings (runtime only — does not persist to YAML)."""
    settings = _get_settings()
    cfg = settings.provider.pop3
    patch = body.model_dump(exclude_none=True)

    for key, value in patch.items():
        if hasattr(cfg, key):
            object.__setattr__(cfg, key, value)

    return Pop3SettingsResponse(
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        tls_mode=cfg.tls_mode,
        connect_timeout_seconds=cfg.connect_timeout_seconds,
        max_messages_per_poll=cfg.max_messages_per_poll,
    )


@router.post("/accounts/pop3/test")
async def test_pop3_connection(
    body: Pop3TestRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Test POP3 connectivity using provided or current credentials."""
    from config.settings import Pop3Config
    from app.adapters.inbound.pop3 import POP3InboundAdapter
    from app.adapters.inbound.seen_store import MemorySeenStore

    settings = _get_settings()
    cfg = settings.provider.pop3

    # Merge provided overrides with current config
    test_config = Pop3Config(
        host=body.host if body and body.host else cfg.host,
        port=body.port if body and body.port else cfg.port,
        username=body.username if body and body.username else cfg.username,
        password=body.password if body and body.password else cfg.password,
        tls_mode=body.tls_mode if body and body.tls_mode else cfg.tls_mode,
        connect_timeout_seconds=cfg.connect_timeout_seconds,
        max_messages_per_poll=cfg.max_messages_per_poll,
    )

    adapter = POP3InboundAdapter(config=test_config, seen_store=MemorySeenStore())
    result = await adapter.health_check()

    if result.status == "ok":
        return {"status": "ok", "latency_ms": result.latency_ms}
    else:
        return {"status": "error", "message": result.details.get("error", "Connection failed")}


@router.post("/accounts/pop3/sync")
async def trigger_sync(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Trigger an immediate out-of-cycle poll."""
    poller = _get_poller()
    if poller:
        poller.trigger_immediate_poll()
        return {"triggered": True}
    return {"triggered": False}


@router.get("/accounts/pop3/status", response_model=Pop3StatusResponse)
async def get_pop3_status(
    user: AuthenticatedUser = Depends(get_current_user),
) -> Pop3StatusResponse:
    """Return current poller status."""
    poller = _get_poller()
    if not poller:
        return Pop3StatusResponse()

    return Pop3StatusResponse(
        last_poll_at=poller.last_poll_at.isoformat() if poller.last_poll_at else None,
        last_poll_status=poller.last_poll_status,
        last_error=poller.last_error,
        messages_last_cycle=poller.messages_last_cycle,
        is_polling=poller.is_polling,
    )
