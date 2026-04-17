"""PSense Mail — Idempotency middleware.

Enforces and caches Idempotency-Key on mutating HTTP methods (POST, PATCH, DELETE).

Behaviour
---------
1. If the request carries an Idempotency-Key header and a cached record exists
   with a matching response, the cached response is returned immediately with
   X-Idempotency-Replay: true (no handler is called).

2. If the request carries a key but no record exists, the request is forwarded
   to the handler. After the handler returns a 2xx response, the key + response
   body are persisted to the IdempotencyRecord collection (TTL 24 h).

3. If no key is present the request proceeds normally. Routes can enforce the
   key's presence at the router level for critical mutations.

Key format: any string ≤ 128 chars; convention is a UUID v4.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
MAX_KEY_LEN = 128


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Read-through/write-through idempotency cache using MongoDB."""

    # Paths exempt from idempotency caching even if they are mutating.
    # Health + admin reads + sync are always safe to re-run.
    SKIP_PATHS_PREFIX = (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/admin/health",
        "/api/v1/sync",
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PATHS_PREFIX):
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key", "").strip()
        if not idem_key:
            # No key — proceed; some routes explicitly require it (enforced at route level)
            return await call_next(request)

        if len(idem_key) > MAX_KEY_LEN:
            return JSONResponse(
                status_code=400,
                content={"error": "Idempotency-Key exceeds 128 characters", "code": "VALIDATION_ERROR"},
            )

        user = getattr(request.state, "user", None)
        user_id = user.user_id if user else "anonymous"
        tenant_id = getattr(user, "tenant_id", "default") or "default"

        # Composite cache key: per-tenant + per-user + client key
        cache_key = f"{tenant_id}:{user_id}:{idem_key}"
        cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()

        try:
            from app.domain.models import IdempotencyRecord

            existing = await IdempotencyRecord.find_one({"_id": cache_hash})
            if existing and existing.response_json:
                logger.debug("Idempotency cache hit: key=%s", idem_key)
                try:
                    body = json.loads(existing.response_json)
                    return JSONResponse(
                        status_code=200,
                        content=body,
                        headers={"X-Idempotency-Replay": "true", "X-Correlation-ID": existing.id},
                    )
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Failed to replay idempotency record: %s", exc)
                    # Fall through to normal processing
        except Exception as exc:
            # DB unavailable — degrade gracefully, proceed without cache
            logger.warning("Idempotency DB read failed (degraded): %s", exc)

        response = await call_next(request)

        # Cache 2xx responses only
        if 200 <= response.status_code < 300:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk

                response_text = body_bytes.decode("utf-8")

                from app.domain.models import IdempotencyRecord

                expires = datetime.now(timezone.utc) + timedelta(hours=24)
                try:
                    await IdempotencyRecord(
                        id=cache_hash,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        operation=path,
                        request_hash=idem_key,
                        response_json=response_text,
                        expires_at=expires,
                    ).insert()
                except Exception:
                    pass  # Duplicate key from concurrent request — safe to ignore

                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as exc:
                logger.warning("Idempotency DB write failed (degraded): %s", exc)

        return response
