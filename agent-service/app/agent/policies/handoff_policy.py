"""Deterministic handoff decisions.

Every trigger in this module maps to a fixed, machine-readable reason and a
templated (never LLM-generated) user-facing message and summary — per
backend-dev.yaml: "make retry, failure and handoff decisions deterministic"
and "every handoff must have a machine-readable reason ... a user-safe
explanation ... a concise conversation summary." None of this is an LLM
judgment call; the orchestrator only feeds in *signals* (e.g. a
record_lead_info.requests_human flag), the decision itself lives here.
"""
from __future__ import annotations

from typing import Literal

from app.domain.models import Conversation, HandoffReason, HandoffReasonBusiness, HandoffReasonTechnical, HandoffRecord
from app.observability.redact import redact_cep, redact_pii

_HUMAN_REQUEST_KEYWORDS = (
    "atendente",
    "humano",
    "pessoa de verdade",
    "falar com alguém",
    "falar com alguem",
    "quero um humano",
    "supervisor",
)

_USER_MESSAGES: dict[HandoffReason, str] = {
    HandoffReasonTechnical.QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES: (
        "Nosso sistema de cotação está indisponível no momento, mesmo depois de "
        "algumas tentativas. Já registrei tudo o que você me contou e um "
        "atendente vai continuar seu atendimento e te enviar a cotação assim "
        "que possível."
    ),
    HandoffReasonTechnical.INVALID_QUOTE_SERVICE_RESPONSE: (
        "Recebi uma resposta inesperada do nosso sistema de cotação. Para não "
        "te passar uma informação errada, vou transferir você para um "
        "atendente humano continuar daqui."
    ),
    HandoffReasonTechnical.UNRECOVERABLE_INTEGRATION_FAILURE: (
        "Encontrei um problema técnico que não consigo resolver sozinho agora. "
        "Um atendente vai assumir a conversa para te ajudar."
    ),
    HandoffReasonTechnical.CONVERSATION_STATE_INCONSISTENT: (
        "Preciso transferir você para um atendente humano para continuar com "
        "segurança a partir daqui."
    ),
    HandoffReasonBusiness.LEAD_REQUESTS_HUMAN: (
        "Sem problema! Vou te passar para um atendente humano."
    ),
    HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN: (
        "Pelas informações que você me passou, não consigo fechar essa cotação "
        "automaticamente: {refusal_reason} Um atendente vai entrar em contato "
        "para ver se existe alguma alternativa."
    ),
    HandoffReasonBusiness.REQUIRED_INFORMATION_CANNOT_BE_CONFIRMED: (
        "Não consegui confirmar uma informação necessária para calcular sua "
        "cotação. Vou te transferir para um atendente humano continuar por "
        "aqui."
    ),
    HandoffReasonBusiness.AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD: (
        "Acho melhor um atendente humano continuar essa conversa com você a "
        "partir daqui."
    ),
    HandoffReasonBusiness.SCENARIO_OUTSIDE_SUPPORTED_SCOPE: (
        "Esse assunto foge do que consigo resolver por aqui. Um atendente "
        "humano vai te ajudar."
    ),
}


def detect_human_request_keywords(text: str) -> bool:
    """Cheap pre-LLM fast path for an explicit ask for a human. Defensive
    only — natural-language detection of this intent is primarily the LLM's
    job via record_lead_info.requests_human; this is a safety net, not the
    primary signal."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in _HUMAN_REQUEST_KEYWORDS)


def render_user_message(reason: HandoffReason, *, refusal_reason: str | None = None) -> str:
    template = _USER_MESSAGES[reason]
    if "{refusal_reason}" in template:
        return template.format(refusal_reason=refusal_reason or "o motivo não foi detalhado.")
    return template


def render_summary(conversation: Conversation, reason: HandoffReason, *, last_lead_message: str | None) -> str:
    """The lead_profile fields quoted here are the agent's own confirmed
    qualification data, not incidental PII, so they're not run through
    redact_pii (that's for free text). CEP is the one exception: it's
    precise enough to identify an address, so the summary handed to a
    human operator only ever gets its 2-digit region prefix via
    redact_cep — the full CEP stays in LeadProfile/QuoteRequestPayload,
    where it's legitimately needed for quoting."""
    profile = conversation.lead_profile
    vehicle = profile.veiculo_ano if profile.veiculo_ano is not None else "não informado"
    age = profile.idade if profile.idade is not None else "não informada"
    cep = redact_cep(profile.cep) or "não informado"
    plan = profile.plano_id.value if profile.plano_id else "não definido"
    last_message_excerpt = redact_pii(last_lead_message or "")[:200]
    return (
        f"Lead informou: veículo ano {vehicle}, idade {age}, região do CEP {cep}, "
        f"plano {plan}. Motivo do encaminhamento: {reason.value}. "
        f"Última mensagem do lead: '{last_message_excerpt}'."
    )


def create_handoff_record(
    conversation: Conversation,
    *,
    category: Literal["technical", "business"],
    reason: HandoffReason,
    refusal_reason: str | None = None,
    last_lead_message: str | None = None,
) -> HandoffRecord:
    return HandoffRecord(
        conversation_id=conversation.id,
        category=category,
        reason=reason,
        user_message=render_user_message(reason, refusal_reason=refusal_reason),
        summary=render_summary(conversation, reason, last_lead_message=last_lead_message),
        lead_profile_snapshot=conversation.lead_profile.model_copy(deep=True),
    )
