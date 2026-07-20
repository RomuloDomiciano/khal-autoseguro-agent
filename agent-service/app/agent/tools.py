"""Tool specs exposed to the LLM, plus the glue that applies/validates a
model's tool-call arguments against domain state. No MCP, no generic tool
framework — two hand-written tools are enough for this challenge.

record_lead_info is a pure structured-extraction channel: it touches no
external system, only updates LeadProfile. get_quote is intercepted by the
orchestrator, which validates its arguments against the already-confirmed
LeadProfile *before* executing anything — see get_quote_args_match_profile.
This guards against the model inventing or silently mutating values on the
one tool call that actually reaches an external system.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.domain.models import LeadProfile, PlanoId, QuoteRequestPayload
from app.integrations.llm.base import ToolSpec

RECORD_LEAD_INFO = ToolSpec(
    name="record_lead_info",
    description=(
        "Registra informações extraídas da mensagem mais recente do lead: "
        "ano do veículo, idade, CEP, plano escolhido, pedido explícito de "
        "atendimento humano, ou assunto fora do escopo deste atendimento. "
        "Chame sempre que identificar qualquer uma dessas informações, "
        "mesmo que mais de uma apareça na mesma mensagem."
    ),
    parameters={
        "type": "object",
        "properties": {
            "veiculo_ano": {"type": "integer", "description": "Ano de fabricação do veículo, ex: 2018"},
            "idade": {"type": "integer", "description": "Idade do lead em anos"},
            "cep": {"type": "string", "description": "CEP do lead, ex: 01310-100"},
            "plano_id": {
                "type": "string",
                "enum": ["essencial", "completo", "premium"],
                "description": "Plano escolhido explicitamente pelo lead",
            },
            "requests_human": {
                "type": "boolean",
                "description": "true se o lead pediu explicitamente para falar com um atendente humano",
            },
            "out_of_scope_topic": {
                "type": "boolean",
                "description": (
                    "true se o lead está perguntando sobre algo fora do escopo "
                    "(ex: sinistro, cancelamento, outro tipo de seguro)"
                ),
            },
        },
        "additionalProperties": False,
    },
)

GET_QUOTE = ToolSpec(
    name="get_quote",
    description=(
        "Solicita uma cotação real ao quote-service. Só deve ser chamada "
        "depois que veiculo_ano, idade e plano_id já foram confirmados pelo "
        "lead nesta conversa, com os MESMOS valores já registrados. O "
        "resultado desta ferramenta é a única fonte de verdade para preço — "
        "nunca informe um valor que não tenha vindo dela."
    ),
    parameters={
        "type": "object",
        "properties": {
            "plano_id": {"type": "string", "enum": ["essencial", "completo", "premium"]},
            "idade": {"type": "integer"},
            "veiculo_ano": {"type": "integer"},
            "cep": {"type": "string"},
        },
        "required": ["plano_id", "idade", "veiculo_ano"],
        "additionalProperties": False,
    },
)

TOOL_SPECS: list[ToolSpec] = [RECORD_LEAD_INFO, GET_QUOTE]


class RecordLeadInfoArgs(BaseModel):
    veiculo_ano: int | None = Field(default=None, ge=1950, le=2100)
    idade: int | None = Field(default=None, ge=0, le=200)
    cep: str | None = None
    plano_id: PlanoId | None = None
    requests_human: bool = False
    out_of_scope_topic: bool = False


class GetQuoteArgs(BaseModel):
    plano_id: PlanoId
    idade: int = Field(ge=0, le=200)
    veiculo_ano: int = Field(ge=1950, le=2100)
    cep: str | None = None


class ToolArgumentError(Exception):
    """Raised when the model's tool-call arguments don't parse — treated as
    'extraction failed this turn', never as a crash."""


def parse_record_lead_info_args(raw_args: dict) -> RecordLeadInfoArgs:
    try:
        return RecordLeadInfoArgs.model_validate(raw_args)
    except ValidationError as exc:
        raise ToolArgumentError(str(exc)) from exc


def apply_record_lead_info(profile: LeadProfile, args: RecordLeadInfoArgs) -> LeadProfile:
    updated = profile.model_copy(deep=True)
    if args.veiculo_ano is not None:
        updated.veiculo_ano = args.veiculo_ano
    if args.idade is not None:
        updated.idade = args.idade
    if args.cep is not None:
        updated.cep = args.cep
    if args.plano_id is not None:
        updated.plano_id = args.plano_id
    return updated


def parse_get_quote_args(raw_args: dict) -> GetQuoteArgs:
    try:
        return GetQuoteArgs.model_validate(raw_args)
    except ValidationError as exc:
        raise ToolArgumentError(str(exc)) from exc


def get_quote_args_match_profile(args: GetQuoteArgs, profile: LeadProfile) -> bool:
    """The orchestrator's guard against the model inventing or mutating
    values on the one tool call that reaches an external system: the
    arguments passed to get_quote must exactly match what was already
    confirmed in LeadProfile."""
    return (
        args.plano_id == profile.plano_id
        and args.idade == profile.idade
        and args.veiculo_ano == profile.veiculo_ano
        and _normalize_cep(args.cep) == _normalize_cep(profile.cep)
    )


def to_quote_request_payload(args: GetQuoteArgs) -> QuoteRequestPayload:
    # data_inicio is deliberately absent from GetQuoteArgs (see GET_QUOTE's
    # tool spec above) and never set here: it drives quote-service's
    # pro-rata first-payment math, and the agent has no confirmed-profile
    # value to validate it against, so accepting it from the LLM would let
    # the model silently pick the price shown to the lead.
    return QuoteRequestPayload(
        plano_id=args.plano_id,
        idade=args.idade,
        veiculo_ano=args.veiculo_ano,
        cep=args.cep,
    )


def _normalize_cep(cep: str | None) -> str | None:
    return cep or None
