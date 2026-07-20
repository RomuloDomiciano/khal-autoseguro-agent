"""Scriptable QuoteServiceClient test double for orchestrator tests — the
real client's behavior against the real quote-service is already proven in
tests/integration/test_quote_service_client.py; here we only need to
control what the orchestrator sees.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Union

from app.domain.models import QuoteRequestPayload
from app.integrations.quote_service.client import QuoteServiceOutcome

Scripted = Union[QuoteServiceOutcome, Callable[[QuoteRequestPayload], QuoteServiceOutcome]]


class FakeQuoteServiceClient:
    def __init__(self, outcomes: list[Scripted]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[QuoteRequestPayload] = []

    async def get_plans(self) -> dict:
        return {}

    async def health(self) -> bool:
        return True

    async def request_quote(
        self, payload: QuoteRequestPayload, *, conversation_id: str, quote_request_id: str
    ) -> QuoteServiceOutcome:
        self.calls.append(payload)
        if not self._outcomes:
            raise AssertionError("FakeQuoteServiceClient ran out of scripted outcomes")
        next_outcome = self._outcomes.pop(0)
        if callable(next_outcome):
            return next_outcome(payload)
        return next_outcome
