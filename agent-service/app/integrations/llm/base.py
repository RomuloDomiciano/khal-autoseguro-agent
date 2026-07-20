"""Provider-agnostic LLM client interface.

Everything the orchestrator needs from "an LLM" is expressed here. Adding a
second provider later (e.g. Anthropic) means one new module implementing
`LLMClient` plus one branch in `factory.py` — conversation state, field
validation, quote-request construction, quote-service integration,
timeout/retry policy, handoff policy, and observability all stay untouched.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class LLMToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[LLMToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class LLMToolResult(BaseModel):
    finish_reason: Literal["stop", "tool_calls", "length", "content_filter"]
    message: LLMMessage
    usage: dict[str, int] | None = None


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> LLMToolResult: ...
