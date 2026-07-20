from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.config.settings import Settings
from app.integrations.llm.base import LLMMessage, LLMToolCall, LLMToolResult, ToolSpec

_FINISH_REASON_MAP: dict[str, str] = {
    "stop": "stop",
    "tool_calls": "tool_calls",
    "length": "length",
    "content_filter": "content_filter",
}


class OpenAIChatClient:
    """LLMClient implementation backed by the OpenAI Chat Completions API."""

    def __init__(self, settings: Settings) -> None:
        # A missing key must not crash service startup — the SDK requires a
        # non-empty string at construction time, but the actual failure (if
        # the key is genuinely absent/invalid) belongs at call time, where
        # the orchestrator already handles LLM failures safely.
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key or "not-configured",
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        self._model = settings.llm_model

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> LLMToolResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[self._to_openai_message(m) for m in messages],
            tools=[self._to_openai_tool(t) for t in tools] or None,
            tool_choice="auto" if tools else None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = (
            {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            if response.usage
            else None
        )
        return LLMToolResult(
            finish_reason=_FINISH_REASON_MAP.get(choice.finish_reason, "stop"),
            message=self._from_openai_message(choice.message),
            usage=usage,
        )

    @staticmethod
    def _to_openai_message(message: LLMMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in message.tool_calls
            ]
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        if message.name:
            payload["name"] = message.name
        return payload

    @staticmethod
    def _to_openai_tool(tool: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @staticmethod
    def _from_openai_message(message: Any) -> LLMMessage:
        tool_calls: list[LLMToolCall] | None = None
        if message.tool_calls:
            tool_calls = [
                LLMToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=json.loads(call.function.arguments or "{}"),
                )
                for call in message.tool_calls
            ]
        return LLMMessage(role="assistant", content=message.content, tool_calls=tool_calls)
