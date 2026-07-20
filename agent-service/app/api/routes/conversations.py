from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agent.orchestrator import ConversationOrchestrator
from app.api.dependencies import get_orchestrator
from app.api.schemas import (
    ConversationStateResponse,
    QuoteAttemptOut,
    SendMessageRequest,
    TurnResponse,
    conversation_to_state_response,
    message_to_out,
    quote_attempt_to_out,
)
from app.domain.repository import ConversationNotFoundError

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201, response_model=TurnResponse)
async def create_conversation(orchestrator: ConversationOrchestrator = Depends(get_orchestrator)) -> TurnResponse:
    conversation = await orchestrator.create_conversation()
    return TurnResponse(
        conversation_id=conversation.id,
        status=conversation.status,
        messages=[message_to_out(m) for m in conversation.messages],
    )


@router.post("/{conversation_id}/messages", response_model=TurnResponse)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator),
) -> TurnResponse:
    try:
        new_messages = await orchestrator.handle_message(conversation_id, request.body, request.message_type)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation_not_found") from exc

    conversation = await orchestrator.get_conversation(conversation_id)
    return TurnResponse(
        conversation_id=conversation.id,
        status=conversation.status,
        messages=[message_to_out(m) for m in new_messages],
    )


@router.get("/{conversation_id}", response_model=ConversationStateResponse)
async def get_conversation(
    conversation_id: str, orchestrator: ConversationOrchestrator = Depends(get_orchestrator)
) -> ConversationStateResponse:
    try:
        conversation = await orchestrator.get_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation_not_found") from exc
    return conversation_to_state_response(conversation)


@router.get("/{conversation_id}/quote-attempts", response_model=list[QuoteAttemptOut])
async def get_quote_attempts(
    conversation_id: str,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator),
) -> list[QuoteAttemptOut]:
    try:
        conversation = await orchestrator.get_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation_not_found") from exc
    return [quote_attempt_to_out(attempt) for attempt in conversation.quote_attempts]
