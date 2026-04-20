"""PSense Mail — Microsoft Graph inbound adapter.

Uses the Microsoft Graph REST API to fetch mail from Exchange Online /
Microsoft 365 mailboxes. Requires Azure AD app registration with
Mail.ReadWrite and Mail.Send permissions.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage
from app.domain.models import MailRecipient

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphInboundAdapter:
    """Microsoft Graph inbound adapter for Exchange Online / M365."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "",
        scopes: list[str] | None = None,
    ):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = scopes or ["Mail.ReadWrite", "Mail.Send"]
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _ensure_token(self) -> str:
        """Get or refresh OAuth2 client credentials token."""
        import httpx

        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = time.monotonic() + data.get("expires_in", 3600) - 60
            return self._access_token

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        """Fetch unread messages from Microsoft Graph."""
        import httpx

        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Build filter
        filter_parts = ["isRead eq false"]
        if since:
            filter_parts.append(f"receivedDateTime ge {since.isoformat()}")
        odata_filter = " and ".join(filter_parts)

        url = f"{_GRAPH_BASE}/me/messages?$filter={odata_filter}&$top=50&$orderby=receivedDateTime desc"
        url += "&$select=id,subject,bodyPreview,body,from,toRecipients,ccRecipients,receivedDateTime,internetMessageHeaders,internetMessageId"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        messages: list[InboundMessage] = []
        for item in data.get("value", []):
            from_data = item.get("from", {}).get("emailAddress", {})
            to_list = [
                MailRecipient(
                    email=r.get("emailAddress", {}).get("address", ""),
                    name=r.get("emailAddress", {}).get("name", ""),
                )
                for r in item.get("toRecipients", [])
            ]
            cc_list = [
                MailRecipient(
                    email=r.get("emailAddress", {}).get("address", ""),
                    name=r.get("emailAddress", {}).get("name", ""),
                )
                for r in item.get("ccRecipients", [])
            ]

            # Extract headers
            raw_headers: dict[str, str] = {}
            for header in item.get("internetMessageHeaders", []):
                raw_headers[header["name"]] = header["value"]
            if "internetMessageId" in item:
                raw_headers["Message-ID"] = item["internetMessageId"]

            body = item.get("body", {})
            body_html = body.get("content") if body.get("contentType") == "html" else None
            body_text = body.get("content") if body.get("contentType") == "text" else None

            received_str = item.get("receivedDateTime", "")
            received_at = datetime.fromisoformat(received_str.rstrip("Z")).replace(tzinfo=timezone.utc) if received_str else None

            messages.append(InboundMessage(
                provider_message_id=item["id"],
                from_address=from_data.get("address", ""),
                from_name=from_data.get("name", ""),
                to=to_list,
                cc=cc_list,
                subject=item.get("subject", ""),
                body_html=body_html,
                body_text=body_text or item.get("bodyPreview", ""),
                received_at=received_at,
                raw_headers=raw_headers,
            ))

        return messages

    async def acknowledge(self, message_ids: list[str]) -> None:
        """Mark messages as read on Microsoft Graph."""
        import httpx

        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            for mid in message_ids:
                try:
                    await client.patch(
                        f"{_GRAPH_BASE}/me/messages/{mid}",
                        headers=headers,
                        json={"isRead": True},
                    )
                except Exception as exc:
                    logger.warning("Failed to mark message %s as read: %s", mid, exc)

    async def health_check(self) -> AdapterHealthStatus:
        try:
            import httpx
            start = time.monotonic()
            token = await self._ensure_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_GRAPH_BASE}/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                latency = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    return AdapterHealthStatus(name="msgraph_inbound", status="ok", latency_ms=latency)
                return AdapterHealthStatus(
                    name="msgraph_inbound", status="degraded",
                    latency_ms=latency,
                    details={"status_code": resp.status_code},
                )
        except Exception as exc:
            return AdapterHealthStatus(
                name="msgraph_inbound", status="down",
                details={"error": str(exc)},
            )
