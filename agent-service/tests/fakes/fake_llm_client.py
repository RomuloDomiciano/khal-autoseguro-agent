"""Scriptable LLMClient test double. Orchestrator tests use this instead of
a real network call, so tool-calling-loop logic is fully testable without
any dependency on OpenAI being reachable or paid for.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Union

from app.integrations.llm.base import LLMMessage, LLMToolResult, ToolSpec

Scripted = Union[LLMToolResult, Callable[[list[LLMMessage], list[ToolSpec]], LLMToolResult]]


class FakeLLMClient:
    def __init__(self, responses: list[Scripted]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[list[LLMMessage], list[ToolSpec]]] = []

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> LLMToolResult:
        self.calls.append((messages, tools))
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        next_response = self._responses.pop(0)
        if callable(next_response):
            return next_response(messages, tools)
        return next_response
