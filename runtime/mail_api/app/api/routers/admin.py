"""PSense Mail — Admin router.

Health checks, demo data seeding, and diagnostics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.domain.requests import SeedRequest
from app.domain.responses import AdapterHealth, HealthReport, SuccessResponse
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.get("/health", response_model=HealthReport)
async def health_check() -> HealthReport:
    """System health check — no auth required. Includes DB, adapters, workers."""
    from app.main import _registry

    adapter_health: list[AdapterHealth] = []

    # Check database connectivity
    try:
        from app.domain.models import TenantDoc
        import time as _time
        t0 = _time.monotonic()
        await TenantDoc.find_one()
        db_latency = (_time.monotonic() - t0) * 1000
        adapter_health.append(AdapterHealth(
            name="database", status="ok", latency_ms=db_latency,
        ))
    except Exception as e:
        adapter_health.append(AdapterHealth(
            name="database", status="down", details={"error": str(e)},
        ))

    # Check each adapter
    if _registry:
        try:
            transport_health = await _registry.transport.health_check()
            adapter_health.append(AdapterHealth(
                name=transport_health.name, status=transport_health.status,
                latency_ms=transport_health.latency_ms, details=transport_health.details,
            ))
        except Exception as e:
            adapter_health.append(AdapterHealth(name="transport", status="down", details={"error": str(e)}))

        try:
            storage_health = await _registry.file_storage.health_check()
            adapter_health.append(AdapterHealth(
                name=storage_health.name, status=storage_health.status,
                latency_ms=storage_health.latency_ms, details=storage_health.details,
            ))
        except Exception as e:
            adapter_health.append(AdapterHealth(name="file_storage", status="down", details={"error": str(e)}))

        try:
            search_health = await _registry.search.health_check()
            adapter_health.append(AdapterHealth(
                name=search_health.name, status=search_health.status,
                latency_ms=search_health.latency_ms, details=search_health.details,
            ))
        except Exception as e:
            adapter_health.append(AdapterHealth(name="search", status="down", details={"error": str(e)}))

    overall = "ok"
    if any(a.status == "down" for a in adapter_health):
        overall = "down"
    elif any(a.status == "degraded" for a in adapter_health):
        overall = "degraded"

    return HealthReport(status=overall, adapters=adapter_health, timestamp=datetime.now(timezone.utc))


@router.post("/admin/seed", response_model=dict[str, Any])
async def seed_demo(
    body: SeedRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Seed demo data for the authenticated user."""
    from app.seed.demo_data import seed_demo_data

    result = await seed_demo_data(user.user_id)
    return {"status": "ok", **result}


@router.get("/admin/diagnostics")
async def diagnostics(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """System diagnostics (admin only)."""
    from app.domain.models import MessageDoc, FolderDoc, ThreadDoc

    msg_count = await MessageDoc.find(MessageDoc.user_id == user.user_id).count()
    folder_count = await FolderDoc.find(FolderDoc.user_id == user.user_id).count()
    thread_count = await ThreadDoc.find(ThreadDoc.user_id == user.user_id).count()

    return {
        "user_id": user.user_id,
        "message_count": msg_count,
        "folder_count": folder_count,
        "thread_count": thread_count,
    }


@router.get("/admin/gdpr/export")
async def gdpr_export(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """GDPR data export — returns all user data as structured JSON."""
    from app.services.gdpr_service import GDPRExportService
    service = GDPRExportService()
    return await service.export_user_data(user.user_id)


@router.delete("/admin/gdpr/erase")
async def gdpr_erase(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """GDPR right to erasure — permanently delete all user data."""
    from app.services.gdpr_service import GDPRExportService
    service = GDPRExportService()
    counts = await service.delete_user_data(user.user_id)
    return {"status": "erased", "deleted_counts": counts}


@router.get("/admin/dlq")
async def list_dead_letters(
    queue: str | None = None,
    limit: int = 50,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List dead-letter queue entries."""
    from app.domain.models import DeadLetterDoc
    filters: dict[str, Any] = {"resolved_at": None}
    if queue:
        filters["queue"] = queue
    docs = await DeadLetterDoc.find(filters).sort(
        [("created_at", -1)]
    ).limit(limit).to_list()
    return {"items": [d.model_dump(mode="json") for d in docs]}


@router.post("/admin/dlq/{entry_id}/retry")
async def retry_dead_letter(
    entry_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retry a dead-letter queue entry."""
    from app.domain.models import DeadLetterDoc
    doc = await DeadLetterDoc.find_one(DeadLetterDoc.id == entry_id)
    if not doc:
        return {"error": "Not found"}
    doc.retry_count += 1
    doc.last_attempt_at = datetime.now(timezone.utc)
    await doc.save()
    return {"status": "retry_queued", "retry_count": doc.retry_count}


@router.post("/admin/dlq/{entry_id}/resolve")
async def resolve_dead_letter(
    entry_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark a dead-letter entry as resolved."""
    from app.domain.models import DeadLetterDoc
    doc = await DeadLetterDoc.find_one(DeadLetterDoc.id == entry_id)
    if not doc:
        return {"error": "Not found"}
    doc.resolved_at = datetime.now(timezone.utc)
    await doc.save()
    return {"status": "resolved"}
