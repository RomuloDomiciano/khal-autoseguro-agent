"""API-facing DTOs. Deliberately separate from app.domain.models: the wire
format is camelCase (to stay compatible with the existing frontend mock's
TypeScript types), while internal domain models stay snake_case Python.
This module is the only place that mapping happens.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.domain.models import (
    Conversation,
    ConversationStatus,
    ErrorClass,
    HandoffRecord,
    Message,
    MessageKind,
    MessageRole,
    PlanoId,
    QuoteAttempt,
    QuoteAttemptStatus,
)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class QuoteSummaryOut(CamelModel):
    plano_id: PlanoId
    plano_nome: str
    premio_mensal: float
    franquia: float
    coberturas: list[str]
    carencia_dias: int
    moeda: str


class MessageOut(CamelModel):
    id: str
    role: MessageRole
    kind: MessageKind
    body: str
    quote_summary: QuoteSummaryOut | None = None
    created_at: datetime


class LeadProfileOut(CamelModel):
    veiculo_ano: int | None
    idade: int | None
    cep: str | None
    plano_id: PlanoId | None


class HandoffOut(CamelModel):
    id: str
    category: str
    reason: str
    user_message: str
    # Context for the human operator picking up the conversation: a
    # templated (never LLM-generated) recap of the profile collected so far
    # and the reason for the transfer. Any free-text lead message quoted
    # inside it has already been redacted (see redact_pii) before this was
    # ever stored — safe to expose as-is.
    summary: str


class QuoteAttemptOut(CamelModel):
    quote_request_id: str
    attempt_number: int
    status: QuoteAttemptStatus
    http_status: int | None
    error_class: ErrorClass | None
    latency_ms: int | None
    created_at: datetime


class SendMessageRequest(CamelModel):
    body: str
    message_type: str = "text"


class TurnResponse(CamelModel):
    conversation_id: str
    status: ConversationStatus
    messages: list[MessageOut]


class ConversationStateResponse(CamelModel):
    conversation_id: str
    status: ConversationStatus
    lead_profile: LeadProfileOut
    messages: list[MessageOut]
    quote_attempts: list[QuoteAttemptOut]
    handoff: HandoffOut | None


def message_to_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        kind=message.kind,
        body=message.body,
        quote_summary=QuoteSummaryOut(**message.quote_summary.model_dump()) if message.quote_summary else None,
        created_at=message.created_at,
    )


def quote_attempt_to_out(attempt: QuoteAttempt) -> QuoteAttemptOut:
    return QuoteAttemptOut(
        quote_request_id=attempt.quote_request_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        http_status=attempt.http_status,
        error_class=attempt.error_class,
        latency_ms=attempt.latency_ms,
        created_at=attempt.created_at,
    )


def handoff_to_out(handoff: HandoffRecord) -> HandoffOut:
    return HandoffOut(
        id=handoff.id,
        category=handoff.category,
        reason=handoff.reason.value,
        user_message=handoff.user_message,
        summary=handoff.summary,
    )


def conversation_to_state_response(conversation: Conversation) -> ConversationStateResponse:
    return ConversationStateResponse(
        conversation_id=conversation.id,
        status=conversation.status,
        lead_profile=LeadProfileOut(**conversation.lead_profile.model_dump(exclude={"field_attempts"})),
        messages=[message_to_out(m) for m in conversation.messages],
        quote_attempts=[quote_attempt_to_out(a) for a in conversation.quote_attempts],
        handoff=handoff_to_out(conversation.handoff) if conversation.handoff else None,
    )
