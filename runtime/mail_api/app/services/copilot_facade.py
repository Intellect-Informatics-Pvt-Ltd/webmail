"""PSense Mail — AI Copilot facade.

Provides email summarisation, smart reply suggestions, and priority scoring
via a pluggable LLM adapter (OpenAI or NoOp for dev/test).
"""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.protocols import LLMAdapter
from app.domain.errors import NotFoundError
from app.domain.models import MessageDoc

logger = logging.getLogger(__name__)


class CopilotFacade:
    """AI copilot — summarise, suggest replies, score priority."""

    def __init__(self, llm: LLMAdapter):
        self._llm = llm

    async def _get_message(self, message_id: str, user_id: str) -> MessageDoc:
        msg = await MessageDoc.find_one(
            MessageDoc.id == message_id,
            MessageDoc.user_id == user_id,
        )
        if not msg:
            raise NotFoundError(f"Message {message_id} not found")
        return msg

    # ── Summarise ─────────────────────────────────────────────────────

    async def summarise_message(self, message_id: str, user_id: str) -> dict[str, str]:
        """Return a ≤3 sentence summary of the message."""
        msg = await self._get_message(message_id, user_id)
        body = msg.body_text or msg.body_html or ""
        if not body:
            return {"summary": ""}

        prompt = (
            "Summarise the following email in at most 3 sentences. "
            "Return only the summary text, no preamble.\n\n"
            f"Subject: {msg.subject}\n"
            f"From: {msg.sender.email}\n\n"
            f"{body[:4000]}"
        )
        summary = await self._llm.complete(prompt, max_tokens=200)
        return {"summary": summary.strip()}

    # ── Smart Replies ─────────────────────────────────────────────────

    async def suggest_replies(
        self, message_id: str, user_id: str, count: int = 3,
    ) -> dict[str, list[str]]:
        """Return up to `count` short reply suggestions."""
        msg = await self._get_message(message_id, user_id)
        body = msg.body_text or msg.body_html or ""
        if not body:
            return {"suggestions": []}

        prompt = (
            f"Given this email, suggest exactly {count} short professional reply options. "
            "Return each reply on its own line, numbered 1) 2) 3). "
            "Each reply should be 1-2 sentences.\n\n"
            f"Subject: {msg.subject}\n"
            f"From: {msg.sender.email}\n\n"
            f"{body[:4000]}"
        )
        raw = await self._llm.complete(prompt, max_tokens=400)
        suggestions: list[str] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            # Strip numbering prefix like "1) " or "1. "
            if line and line[0].isdigit():
                line = line.lstrip("0123456789.)- ").strip()
            if line:
                suggestions.append(line)
        return {"suggestions": suggestions[:count]}

    # ── Priority Scoring ──────────────────────────────────────────────

    async def score_priority(self, message_id: str, user_id: str) -> dict[str, Any]:
        """Return a priority score (0.0–1.0) and a short reason."""
        msg = await self._get_message(message_id, user_id)
        body = msg.body_text or msg.body_html or ""

        prompt = (
            "Rate the urgency/importance of this email on a scale of 0.0 to 1.0. "
            "Return a JSON object with keys 'score' (float) and 'reason' (string, 1 sentence). "
            "Return ONLY the JSON, no markdown or preamble.\n\n"
            f"Subject: {msg.subject}\n"
            f"From: {msg.sender.email}\n"
            f"Importance: {msg.importance.value}\n\n"
            f"{body[:3000]}"
        )
        raw = await self._llm.complete(prompt, max_tokens=150)

        # Parse — fallback gracefully
        try:
            import json
            data = json.loads(raw.strip())
            score = max(0.0, min(1.0, float(data.get("score", 0.5))))
            reason = str(data.get("reason", ""))
        except Exception:
            score = 0.5
            reason = ""

        return {"score": score, "reason": reason}
