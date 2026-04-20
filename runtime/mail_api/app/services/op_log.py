"""PSense Mail — Op-log service helper.

Provides append_op() which is called from every mutating facade method.
Writes an OpLogEntry alongside the mutation so the delta sync endpoint
can stream changes to clients.

Uses SequenceDoc with atomic $inc for monotonic sequence numbers,
guaranteeing gap-free ordering per (tenant_id, account_id).

Usage in a facade:
    from app.services.op_log import append_op
    await append_op(
        tenant_id=ctx.tenant_id,
        account_id=ctx.account_id,
        kind=OpLogKind.UPSERT,
        entity=OpLogEntity.MESSAGE,
        entity_id=doc.id,
        payload=doc.model_dump(mode="json"),
    )
"""
from __future__ import annotations

import logging
from typing import Any

from app.domain.enums import OpLogEntity, OpLogKind
from app.domain.models import OpLogEntry, SequenceDoc

logger = logging.getLogger(__name__)


async def _next_seq(tenant_id: str, account_id: str) -> int:
    """Atomically increment and return the next sequence number."""
    seq_id = f"{tenant_id}:{account_id}"
    result = await SequenceDoc.get_motor_collection().find_one_and_update(
        {"_id": seq_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


async def append_op(
    *,
    tenant_id: str,
    account_id: str,
    kind: OpLogKind,
    entity: OpLogEntity,
    entity_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a single op-log entry with a monotonic sequence number.

    Fire-and-forget from the caller's perspective — errors are logged
    but never propagate to the mutation caller.
    """
    try:
        seq = await _next_seq(tenant_id, account_id)
        await OpLogEntry(
            tenant_id=tenant_id,
            account_id=account_id,
            seq=seq,
            kind=kind,
            entity=entity,
            entity_id=entity_id,
            payload=payload or {},
        ).insert()
    except Exception as exc:
        # Never let op-log failures break mutations
        logger.warning(
            "Op-log append failed (entity=%s id=%s): %s", entity, entity_id, exc
        )
