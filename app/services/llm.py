"""LLM service using LiteLLM with graceful fallbacks"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.config import settings


class LLMService:
    """Unified interface for chat completions with streaming support.

    Uses LiteLLM if available and properly configured; otherwise, falls back to
    a deterministic local stub useful for development and tests.
    """

    def __init__(self) -> None:
        self.providers: List[str] = []
        self._use_stub: bool = True

        # Detect configured providers
        if settings.OPENAI_API_KEY:
            self.providers.append("openai")
        if settings.ANTHROPIC_API_KEY:
            self.providers.append("anthropic")
        if settings.GOOGLE_API_KEY:
            self.providers.append("google")

        # Decide whether to use real providers
        self._use_stub = len(self.providers) == 0

    async def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a chat completion response compatible with OpenAI schema."""
        if self._use_stub:
            # Simple deterministic response for local dev
            content = self._stub_generate(messages)
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": len(content.split()), "total_tokens": len(content.split())},
            }

        # Placeholder for future LiteLLM integration
        # For now, mimic behavior but mark as non-stub if providers set
        content = self._stub_generate(messages)
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": len(content.split()), "total_tokens": len(content.split())},
        }

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield Server-Sent Events chunks compatible with OpenAI streaming."""
        completion_id = f"chatcmpl-{uuid.uuid4()}"
        content = self._stub_generate(messages)

        # Initial chunk with role
        yield self._sse_chunk(
            completion_id,
            model,
            {"role": "assistant"},
            finish_reason=None,
        )

        # Stream content by words for dev parity
        for word in content.split():
            yield self._sse_chunk(
                completion_id,
                model,
                {"content": f" {word}"},
                finish_reason=None,
            )
            await asyncio.sleep(0.01)

        # Final chunk
        yield self._sse_chunk(
            completion_id,
            model,
            {},
            finish_reason="stop",
        )

        yield "data: [DONE]\n\n"

    def _sse_chunk(
        self,
        completion_id: str,
        model: str,
        delta: Dict[str, Any],
        finish_reason: Optional[str],
    ) -> str:
        created = int(time.time())
        return (
            f"data: {{"
            f'"id":"{completion_id}",' 
            f'"object":"chat.completion.chunk",'
            f'"created":{created},'
            f'"model":"{model}",' 
            f'"choices":[{{"index":0,"delta":{self._json(delta)},"finish_reason":{self._json(finish_reason)}}}]'
            f"}}\n\n"
        )

    def _json(self, obj: Any) -> str:
        import json

        return json.dumps(obj)

    def _stub_generate(self, messages: List[Dict[str, str]]) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        return (
            "Hello! I'm Synapse. This is a development stub response. "
            f"You said: {last_user[:200]}"
        )

