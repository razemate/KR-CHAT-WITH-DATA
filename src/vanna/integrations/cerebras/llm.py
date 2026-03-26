"""
Cerebras LLM service implementation.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from vanna.core.llm import LlmRequest, LlmResponse, LlmService, LlmStreamChunk
from vanna.core.tool import ToolSchema


class CerebrasLlmService(LlmService):
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model or os.getenv("CEREBRAS_MODEL", "llama3.1-8b")
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        self.timeout = timeout

    def _build_messages(self, request: LlmRequest) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})
        return messages

    async def send_request(self, request: LlmRequest) -> LlmResponse:
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is missing!")

        if request.tools:
            # Instead of crashing, we log a warning and proceed without tools.
            # This allows the fallback chain to continue or at least give a text response.
            import logging
            logging.getLogger("CerebrasLlmService").warning("CerebrasLlmService does not support tool calling; proceeding with text-only mode.")

        messages = self._build_messages(request)
        max_completion_tokens = request.max_tokens or int(
            os.getenv("CEREBRAS_MAX_COMPLETION_TOKENS", "1024")
        )
        temperature = float(os.getenv("CEREBRAS_TEMPERATURE", str(request.temperature)))

        try:
            from cerebras.cloud.sdk import Cerebras
        except Exception as e:
            raise ImportError(
                "cerebras-cloud-sdk package is required. Install with: pip install cerebras-cloud-sdk"
            ) from e

        def _call() -> Any:
            client = Cerebras(api_key=self.api_key)
            return client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_completion_tokens=max_completion_tokens,
                temperature=temperature,
                top_p=1,
                stream=False,
                timeout=self.timeout,
            )

        resp = await asyncio.to_thread(_call)

        content: Optional[str] = None
        finish_reason: Optional[str] = None
        try:
            if getattr(resp, "choices", None):
                choice0 = resp.choices[0]
                msg = getattr(choice0, "message", None)
                content = getattr(msg, "content", None) if msg is not None else None
                finish_reason = getattr(choice0, "finish_reason", None)
        except Exception:
            content = None
            finish_reason = None

        usage: Optional[Dict[str, int]] = None
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "prompt_tokens": int(getattr(u, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(u, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(u, "total_tokens", 0) or 0),
            }

        return LlmResponse(
            content=content,
            tool_calls=None,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
            usage=usage,
        )

    async def stream_request(
        self, request: LlmRequest
    ) -> AsyncGenerator[LlmStreamChunk, None]:
        resp = await self.send_request(request)
        if resp.content:
            yield LlmStreamChunk(content=resp.content, finish_reason=resp.finish_reason)
        else:
            yield LlmStreamChunk(finish_reason=resp.finish_reason or "stop")

    async def validate_tools(self, tools: List[ToolSchema]) -> List[str]:
        return []
