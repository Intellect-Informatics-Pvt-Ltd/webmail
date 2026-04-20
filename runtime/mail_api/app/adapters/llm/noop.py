"""NoOp LLM adapter — returns empty strings for dev/test environments."""
from __future__ import annotations

from app.adapters.protocols import AdapterHealthStatus, LLMAdapter


class NoOpLLMAdapter:
    """Always returns empty strings — used when copilot is disabled."""

    async def complete(self, prompt: str, max_tokens: int = 512) -> str:
        return ""

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="llm-noop", status="ok")
