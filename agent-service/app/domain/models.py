"""Core domain types for the AutoSeguro conversational agent.

These models carry no HTTP or LLM SDK dependency — they're the shared
vocabulary between the orchestrator, the policy modules, and the
integrations layer, and are unit-testable in isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums -------------------------------------------------------------


class ConversationStatus(str, Enum):
    COLLECTING = "collecting"
    QUOTING = "quoting"
    RESOLVED = "resolved"
    HANDED_OFF = "handed_off"


class MessageRole(str, Enum):
    LEAD = "lead"
    AGENT = "agent"
    SYSTEM = "system"


class MessageKind(str, Enum):
    TEXT = "text"
    QUOTE = "quote"
    HANDOFF = "handoff"
    ERROR = "error"


class PlanoId(str, Enum):
    ESSENCIAL = "essencial"
    COMPLETO = "completo"
    PREMIUM = "premium"


class RequiredField(str, Enum):
    VEHICLE_YEAR = "veiculo_ano"
    AGE = "idade"
    CEP = "cep"
    PLAN = "plano_id"


# Fixed collection order — mirrors the existing frontend mock's state
# machine (mockAgent.ts) so the two stay conceptually compatible.
REQUIRED_FIELD_ORDER: tuple[RequiredField, ...] = (
    RequiredField.VEHICLE_YEAR,
    RequiredField.AGE,
    RequiredField.CEP,
    RequiredField.PLAN,
)

# CEP is soft-required: quote-service itself treats a missing CEP as a
# valid input (region multiplier defaults to 1.0), so the agent asks once
# but does not hand off if it's never provided.
SOFT_REQUIRED_FIELDS: frozenset[RequiredField] = frozenset({RequiredField.CEP})


class QuoteAttemptStatus(str, Enum):
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED_TRANSIENT_EXHAUSTED = "failed_transient_exhausted"
    REFUSED = "refused"  # 422 cotacao_recusada — terminal, legitimate business outcome
    REJECTED_INVALID = "rejected_invalid"  # 400 payload_invalido — terminal, our own bug
    INVALID_RESPONSE = "invalid_response"  # 200 but response fails contract validation


class ErrorClass(str, Enum):
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    HTTP_500 = "http_500"
    HTTP_502 = "http_502"
    HTTP_503 = "http_503"
    HTTP_504 = "http_504"
    INVALID_REQUEST = "invalid_request"
    VALIDATION_ERROR = "validation_error"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    INVALID_RESPONSE_CONTRACT = "invalid_response_contract"
    BUSINESS_REFUSAL = "business_refusal"  # 422 — project-specific addition, see retry_policy


class HandoffReasonTechnical(str, Enum):
    QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES = "quote_service_unavailable_after_retries"
    INVALID_QUOTE_SERVICE_RESPONSE = "invalid_quote_service_response"
    UNRECOVERABLE_INTEGRATION_FAILURE = "unrecoverable_integration_failure"
    CONVERSATION_STATE_INCONSISTENT = "conversation_state_inconsistent"


class HandoffReasonBusiness(str, Enum):
    LEAD_REQUESTS_HUMAN = "lead_requests_human"
    UNSUPPORTED_VEHICLE_OR_PLAN = "unsupported_vehicle_or_plan"
    REQUIRED_INFORMATION_CANNOT_BE_CONFIRMED = "required_information_cannot_be_confirmed"
    AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD = "agent_confidence_below_project_threshold"
    SCENARIO_OUTSIDE_SUPPORTED_SCOPE = "scenario_outside_supported_scope"


HandoffReason = HandoffReasonTechnical | HandoffReasonBusiness


# --- Lead qualification --------------------------------------------------


class LeadProfile(BaseModel):
    veiculo_ano: int | None = None
    idade: int | None = None
    cep: str | None = None
    plano_id: PlanoId | None = None
    field_attempts: dict[RequiredField, int] = Field(default_factory=dict)

    def missing_required_fields(self) -> list[RequiredField]:
        missing: list[RequiredField] = []
        for field in REQUIRED_FIELD_ORDER:
            if field in SOFT_REQUIRED_FIELDS:
                continue
            if getattr(self, field.value) is None:
                missing.append(field)
        return missing

    def is_ready_for_quote(self) -> bool:
        return not self.missing_required_fields()

    def attempts_for(self, field: RequiredField) -> int:
        return self.field_attempts.get(field, 0)


# --- Quote-service contract (mirrors quote-service's schema 1:1) --------


class QuoteRequestPayload(BaseModel):
    plano_id: PlanoId
    idade: int = Field(ge=0, le=200)
    veiculo_ano: int = Field(ge=1950, le=2100)
    cep: str | None = None
    # quote-service accepts data_inicio for pro-rata math (see
    # tests/integration/test_quote_service_client.py), but the agent never
    # populates it from LLM tool-call arguments — see
    # app/agent/tools.py::to_quote_request_payload. Kept here only because
    # this model mirrors quote-service's wire contract 1:1.
    data_inicio: str | None = None


class CarenciaInfo(BaseModel):
    coberturas: list[str]
    dias: int
    observacao: str


class ProRataInfo(BaseModel):
    dias_no_mes: int
    dias_cobrados: int
    valor_primeiro_pagamento: float


class QuoteResult(BaseModel):
    plano_id: PlanoId
    plano_nome: str
    premio_mensal: float
    franquia: float
    coberturas: list[str]
    multiplicadores: dict[str, float]
    carencia: CarenciaInfo
    moeda: str
    primeiro_pagamento_pro_rata: ProRataInfo | None = None


# --- Traceability records -------------------------------------------------


class QuoteAttempt(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("qatt"))
    conversation_id: str
    quote_request_id: str
    attempt_number: int
    status: QuoteAttemptStatus
    request_payload: QuoteRequestPayload
    http_status: int | None = None
    error_class: ErrorClass | None = None
    error_detail: str | None = None
    result: QuoteResult | None = None
    # Minted by us only when status == SUCCEEDED — quote-service itself
    # issues no id, so this is explicitly our own traceability identifier,
    # not an upstream one.
    quote_id: str | None = None
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class HandoffRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("hoff"))
    conversation_id: str
    category: Literal["technical", "business"]
    reason: HandoffReason
    user_message: str
    summary: str
    lead_profile_snapshot: LeadProfile
    created_at: datetime = Field(default_factory=_utcnow)


class QuoteSummary(BaseModel):
    """Rendered, lead-facing view of a QuoteResult. Always built by
    render_quote_message() from a real QuoteResult — never authored by the
    LLM. Field names match the existing frontend mock's QuoteSummary type."""

    plano_id: PlanoId
    plano_nome: str
    premio_mensal: float
    franquia: float
    coberturas: list[str]
    carencia_dias: int
    moeda: str


class Message(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("msg"))
    conversation_id: str
    role: MessageRole
    kind: MessageKind
    body: str
    quote_summary: QuoteSummary | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("conv"))
    status: ConversationStatus = ConversationStatus.COLLECTING
    lead_profile: LeadProfile = Field(default_factory=LeadProfile)
    messages: list[Message] = Field(default_factory=list)
    quote_attempts: list[QuoteAttempt] = Field(default_factory=list)
    handoff: HandoffRecord | None = None
    # Consecutive LLM-call failures, reset to 0 on any successful call.
    # Two in a row triggers a technical handoff — see orchestrator.
    llm_failure_count: int = 0
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()
