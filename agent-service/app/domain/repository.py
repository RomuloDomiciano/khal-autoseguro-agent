"""Conversation persistence boundary.

Phase 1 ships only an in-memory implementation — state is lost on restart
and it is not safe across multiple worker processes. This is an explicit,
documented limitation (see README), not an oversight: the Protocol is the
seam a real persistence layer (e.g. Redis, Postgres) plugs into later
without the orchestrator changing at all.
"""
from __future__ import annotations

import asyncio
from typing import Protocol

from app.domain.models import Conversation


class ConversationNotFoundError(Exception):
    def __init__(self, conversation_id: str) -> None:
        self.conversation_id = conversation_id
        super().__init__(f"Conversation '{conversation_id}' not found.")


class ConversationRepository(Protocol):
    async def create(self, conversation: Conversation) -> None: ...

    async def get(self, conversation_id: str) -> Conversation: ...

    async def save(self, conversation: Conversation) -> None: ...

    def lock_for(self, conversation_id: str) -> asyncio.Lock:
        """Returns a per-conversation lock, so concurrent inbound messages
        for the same conversation are processed one at a time — this is
        the actual duplicate-request guard, not quote-service-level
        idempotency (POST /quote itself is a pure computation with no
        side effects, so retrying it is safe on its own)."""
        ...


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def create(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    async def get(self, conversation_id: str) -> Conversation:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def save(self, conversation: Conversation) -> None:
        conversation.touch()
        self._conversations[conversation.id] = conversation

    def lock_for(self, conversation_id: str) -> asyncio.Lock:
        if conversation_id not in self._locks:
            self._locks[conversation_id] = asyncio.Lock()
        return self._locks[conversation_id]
