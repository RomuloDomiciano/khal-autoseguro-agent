from __future__ import annotations

from fastapi import Request

from app.agent.orchestrator import ConversationOrchestrator


def get_orchestrator(request: Request) -> ConversationOrchestrator:
    return request.app.state.orchestrator
