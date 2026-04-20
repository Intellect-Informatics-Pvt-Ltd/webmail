"""PSense Mail — SSE (Server-Sent Events) push notifications router.

Provides a streaming endpoint that clients connect to for real-time
updates. Events are dispatched when messages arrive, folders change,
or threads are updated.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["sse"])

# In-memory subscriber registry — per-user event queues
_subscribers: dict[str, list[asyncio.Queue]] = {}


def publish_event(user_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Publish an SSE event to all connected clients for a user.

    Non-blocking — if a queue is full, the event is dropped for that client.
    """
    queues = _subscribers.get(user_id, [])
    payload = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for user %s, dropping event %s", user_id, event_type)


async def _event_stream(user_id: str, request: Request) -> AsyncGenerator[str, None]:
    """Generate SSE events for a connected client."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)

    if user_id not in _subscribers:
        _subscribers[user_id] = []
    _subscribers[user_id].append(queue)

    try:
        # Send initial keepalive
        yield f"event: connected\ndata: {json.dumps({'user_id': user_id})}\n\n"

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive ping every 30 seconds
                yield f"event: ping\ndata: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"

    finally:
        _subscribers[user_id].remove(queue)
        if not _subscribers[user_id]:
            del _subscribers[user_id]


@router.get("/events/stream")
async def event_stream(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    """SSE endpoint — connect for real-time push notifications.

    Event types: message.new, message.updated, folder.counts, thread.updated, sync.delta
    """
    return StreamingResponse(
        _event_stream(user.user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
