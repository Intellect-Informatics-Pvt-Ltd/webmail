"""OpenAI-compatible LLM adapter.

Works with OpenAI, Azure OpenAI, and any OpenAI-compatible API server
(Ollama, vLLM, LM Studio, text-generation-webui, etc.).
"""
from __future__ import annotations

import logging
import time
from typing import Any

from app.adapters.protocols import AdapterHealthStatus

logger = logging.getLogger(__name__)


class OpenAILLMAdapter:
    """LLM adapter backed by any OpenAI-compatible API.

    Supports:
      - OpenAI (default)
      - Azure OpenAI (via base_url)
      - Ollama (http://localhost:11434/v1)
      - vLLM, LM Studio, text-generation-webui, etc.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ):
        self._api_key = api_key or "ollama"  # Ollama doesn't require a key
        self._model = model
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
                kwargs: dict[str, Any] = {"api_key": self._api_key}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = openai.AsyncOpenAI(**kwargs)
            except ImportError:
                raise RuntimeError("openai package is required for OpenAI-compatible LLM adapter")
        return self._client

    async def complete(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("OpenAI completion failed: %s", exc)
            return ""

    async def health_check(self) -> AdapterHealthStatus:
        t0 = time.monotonic()
        try:
            client = self._get_client()
            # For Ollama/local LLMs, models.list() also works via the /v1/models endpoint
            await client.models.list()
            latency = (time.monotonic() - t0) * 1000
            name = f"llm-{self._base_url or 'openai'}"
            return AdapterHealthStatus(name=name, status="ok", latency_ms=latency)
        except Exception as exc:
            return AdapterHealthStatus(
                name="llm", status="down", details={"error": str(exc)},
            )
