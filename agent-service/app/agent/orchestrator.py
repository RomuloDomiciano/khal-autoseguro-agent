"""The conversation orchestrator — the only place transport, the LLM, and
quote-service integration meet. Routers stay thin; domain/policy modules
have no HTTP or LLM SDK dependency. Retry, failure-classification, and
handoff decisions are made deterministically here and in the policy
modules — never left to LLM judgment.
"""
from __future__ import annotations

import re
import uuid
from typing import Literal

from app.agent.policies.handoff_policy import create_handoff_record, detect_human_request_keywords
from app.agent.prompting import build_system_prompt
from app.agent.rendering import render_quote_message, to_quote_summary
from app.agent.tools import (
    TOOL_SPECS,
    GetQuoteArgs,
    RecordLeadInfoArgs,
    ToolArgumentError,
    apply_record_lead_info,
    get_quote_args_match_profile,
    parse_get_quote_args,
    parse_record_lead_info_args,
    to_quote_request_payload,
)
from app.config.settings import Settings
from app.domain.models import (
    Conversation,
    ConversationStatus,
    HandoffReason,
    HandoffReasonBusiness,
    HandoffReasonTechnical,
    Message,
    MessageKind,
    MessageRole,
    QuoteAttemptStatus,
    QuoteSummary,
    RequiredField,
)
from app.domain.repository import ConversationRepository
from app.integrations.llm.base import LLMClient, LLMMessage, LLMToolCall, LLMToolResult, ToolSpec
from app.integrations.quote_service.client import QuoteServiceClient
from app.observability.logging import get_logger

logger = get_logger(__name__)

GREETING = (
    "Oi! Aqui é da AutoSeguro 👋 Vou te ajudar a cotar o seguro do seu carro. "
    "Pra começar, me conta: qual o modelo e o ano do veículo?"
)

HANDED_OFF_REPLY = "Você já está com um atendente humano. Ele vai continuar por aqui."

_FABRICATION_FALLBACK = "Deixa eu confirmar isso direito antes de te passar um valor — só um instante."

# Belt-and-suspenders only — the real guarantee against fabricated prices is
# structural (see _execute_quote / render_quote_message): a successful quote
# is always rendered from a real QuoteResult, never from LLM text. This scan
# only covers the free-text path (no tool call / non-success turns), and is
# intentionally narrow: it requires a number directly adjacent to an
# unambiguous currency marker, so it doesn't flag ordinary numbers like
# vehicle years, ages, CEPs, or the id-like strings used for traceability.
_PRICE_MENTION_PATTERNS = (
    re.compile(r"R\$\s?\d"),  # R$ 199 / R$199,90
    re.compile(r"\bBRL\s?\d", re.IGNORECASE),  # BRL 199
    re.compile(r"\d[\d.,]*\s*reais\b", re.IGNORECASE),  # 199 reais / 199,90 reais
    re.compile(r"\d[\d.,]*\s*/\s*m[eê]s\b", re.IGNORECASE),  # 199/mês
    re.compile(r"\d[\d.,]*\s+por\s+m[eê]s\b", re.IGNORECASE),  # 199 por mês
    re.compile(r"\bmensalidade\s+de\s+\d", re.IGNORECASE),  # mensalidade de 199
)


def _looks_like_a_price_mention(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PRICE_MENTION_PATTERNS)

GetQuoteOutcome = Literal["terminal", "mismatch", "invalid_args"]


class ConversationOrchestrator:
    def __init__(
        self,
        *,
        llm_client: LLMClient,
        quote_client: QuoteServiceClient,
        repository: ConversationRepository,
        settings: Settings,
        plans_catalog: list[dict] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._quote_client = quote_client
        self._repository = repository
        self._settings = settings
        self._plans_catalog = plans_catalog or []

    async def create_conversation(self) -> Conversation:
        conversation = Conversation()
        self._append(conversation, MessageRole.AGENT, MessageKind.TEXT, GREETING)
        await self._repository.create(conversation)
        logger.info("conversation.created", conversation_id=conversation.id)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation:
        return await self._repository.get(conversation_id)

    async def handle_message(self, conversation_id: str, body: str, message_type: str = "text") -> list[Message]:
        conversation = await self._repository.get(conversation_id)
        lock = self._repository.lock_for(conversation_id)
        async with lock:
            messages = await self._handle_message_locked(conversation, body, message_type)
            await self._repository.save(conversation)
            return messages

    # --- turn handling -------------------------------------------------------

    async def _handle_message_locked(self, conversation: Conversation, body: str, message_type: str) -> list[Message]:
        before_count = len(conversation.messages)
        # Never log the raw message body — only safe, non-content metadata.
        logger.info(
            "message.received",
            conversation_id=conversation.id,
            message_type=message_type,
            char_len=len(body),
        )

        if conversation.status == ConversationStatus.HANDED_OFF:
            self._append(conversation, MessageRole.SYSTEM, MessageKind.TEXT, HANDED_OFF_REPLY)
            return conversation.messages[before_count:]

        if message_type != "text":
            self._append(conversation, MessageRole.LEAD, MessageKind.TEXT, body)
            self._trigger_handoff(
                conversation,
                category="business",
                reason=HandoffReasonBusiness.SCENARIO_OUTSIDE_SUPPORTED_SCOPE,
                last_lead_message=body,
            )
            return conversation.messages[before_count:]

        self._append(conversation, MessageRole.LEAD, MessageKind.TEXT, body)

        if conversation.status == ConversationStatus.COLLECTING and detect_human_request_keywords(body):
            self._trigger_handoff(
                conversation,
                category="business",
                reason=HandoffReasonBusiness.LEAD_REQUESTS_HUMAN,
                last_lead_message=body,
            )
            return conversation.messages[before_count:]

        if conversation.status == ConversationStatus.RESOLVED:
            await self._run_plain_reply_turn(conversation)
            return conversation.messages[before_count:]

        await self._run_collecting_turn(conversation)
        return conversation.messages[before_count:]

    async def _run_plain_reply_turn(self, conversation: Conversation) -> None:
        """After a quote is resolved, follow-up questions get a plain-text
        reply — no tools are offered, so no new quote request can be
        triggered from here."""
        llm_messages = self._build_base_messages(conversation)
        result = await self._call_llm_safely(conversation, llm_messages, tools=[])
        if result is None:
            return
        text = self._sanitize_llm_reply(result.message.content or "")
        self._append(conversation, MessageRole.AGENT, MessageKind.TEXT, text)

    async def _run_collecting_turn(self, conversation: Conversation) -> None:
        base_messages = self._build_base_messages(conversation)
        turn_exchange: list[LLMMessage] = []
        mismatch_count = 0

        for _iteration in range(1, self._settings.max_tool_iterations + 1):
            llm_messages = base_messages + turn_exchange
            result = await self._call_llm_safely(conversation, llm_messages, tools=TOOL_SPECS)
            if result is None:
                return

            if result.finish_reason == "content_filter":
                self._trigger_handoff(
                    conversation,
                    category="business",
                    reason=HandoffReasonBusiness.AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD,
                )
                return

            if not result.message.tool_calls:
                text = self._sanitize_llm_reply(result.message.content or "")
                self._append(conversation, MessageRole.AGENT, MessageKind.TEXT, text)
                return

            turn_exchange.append(result.message)
            pending_before = self._current_pending_field(conversation)
            requests_human = False
            out_of_scope = False
            handled_get_quote = False

            for call in result.message.tool_calls:
                if call.name == "record_lead_info":
                    tool_message, args = self._handle_record_lead_info(conversation, call)
                    turn_exchange.append(tool_message)
                    if args is not None:
                        requests_human = requests_human or args.requests_human
                        out_of_scope = out_of_scope or args.out_of_scope_topic
                elif call.name == "get_quote":
                    outcome = await self._handle_get_quote(conversation, call, turn_exchange)
                    if outcome == "terminal":
                        return
                    if outcome == "mismatch":
                        mismatch_count += 1
                        if mismatch_count >= 2:
                            self._trigger_handoff(
                                conversation,
                                category="technical",
                                reason=HandoffReasonTechnical.CONVERSATION_STATE_INCONSISTENT,
                            )
                            return
                    handled_get_quote = True
                else:
                    turn_exchange.append(
                        LLMMessage(role="tool", tool_call_id=call.id, name=call.name, content='{"error":"unknown_tool"}')
                    )

            if requests_human:
                self._trigger_handoff(conversation, category="business", reason=HandoffReasonBusiness.LEAD_REQUESTS_HUMAN)
                return
            if out_of_scope:
                self._trigger_handoff(
                    conversation, category="business", reason=HandoffReasonBusiness.SCENARIO_OUTSIDE_SUPPORTED_SCOPE
                )
                return

            if not handled_get_quote:
                self._check_field_attempts(conversation, pending_before)
                if conversation.status == ConversationStatus.HANDED_OFF:
                    return

        self._trigger_handoff(
            conversation,
            category="business",
            reason=HandoffReasonBusiness.AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD,
        )

    # --- tool handling ---------------------------------------------------------

    def _handle_record_lead_info(
        self, conversation: Conversation, call: LLMToolCall
    ) -> tuple[LLMMessage, RecordLeadInfoArgs | None]:
        try:
            args = parse_record_lead_info_args(call.arguments)
        except ToolArgumentError as exc:
            logger.info("agent.tool.record_lead_info.invalid_args", conversation_id=conversation.id, detail=str(exc))
            return (
                LLMMessage(role="tool", tool_call_id=call.id, name=call.name, content='{"status":"invalid_arguments"}'),
                None,
            )

        conversation.lead_profile = apply_record_lead_info(conversation.lead_profile, args)
        return (
            LLMMessage(role="tool", tool_call_id=call.id, name=call.name, content='{"status":"recorded"}'),
            args,
        )

    async def _handle_get_quote(
        self, conversation: Conversation, call: LLMToolCall, turn_exchange: list[LLMMessage]
    ) -> GetQuoteOutcome:
        try:
            args = parse_get_quote_args(call.arguments)
        except ToolArgumentError as exc:
            logger.info("agent.tool.get_quote.invalid_args", conversation_id=conversation.id, detail=str(exc))
            turn_exchange.append(
                LLMMessage(role="tool", tool_call_id=call.id, name=call.name, content='{"status":"invalid_arguments"}')
            )
            return "invalid_args"

        if not get_quote_args_match_profile(args, conversation.lead_profile):
            logger.warning("agent.tool.get_quote.arg_mismatch", conversation_id=conversation.id)
            turn_exchange.append(
                LLMMessage(
                    role="tool",
                    tool_call_id=call.id,
                    name=call.name,
                    content='{"status":"rejected","reason":"arguments_do_not_match_confirmed_profile"}',
                )
            )
            return "mismatch"

        await self._execute_quote(conversation, args)
        return "terminal"

    async def _execute_quote(self, conversation: Conversation, args: GetQuoteArgs) -> None:
        conversation.status = ConversationStatus.QUOTING
        payload = to_quote_request_payload(args)
        quote_request_id = f"qreq_{uuid.uuid4().hex[:12]}"

        outcome = await self._quote_client.request_quote(
            payload, conversation_id=conversation.id, quote_request_id=quote_request_id
        )
        conversation.quote_attempts.extend(outcome.attempts)

        if outcome.final_status == QuoteAttemptStatus.SUCCEEDED and outcome.result is not None:
            quote_id = f"qte_{uuid.uuid4().hex[:8]}"
            outcome.attempts[-1].quote_id = quote_id
            summary = to_quote_summary(outcome.result)
            body = render_quote_message(outcome.result)
            self._append(conversation, MessageRole.AGENT, MessageKind.QUOTE, body, quote_summary=summary)
            conversation.status = ConversationStatus.RESOLVED
            logger.info(
                "quote.outcome",
                conversation_id=conversation.id,
                quote_id=quote_id,
                quote_request_id=quote_request_id,
                final_status=outcome.final_status.value,
                total_attempts=len(outcome.attempts),
            )
            return

        if outcome.final_status == QuoteAttemptStatus.REFUSED:
            self._trigger_handoff(
                conversation,
                category="business",
                reason=HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN,
                refusal_reason=outcome.refusal_reason,
            )
            return

        if outcome.final_status == QuoteAttemptStatus.REJECTED_INVALID:
            self._trigger_handoff(
                conversation, category="technical", reason=HandoffReasonTechnical.UNRECOVERABLE_INTEGRATION_FAILURE
            )
            return

        if outcome.final_status == QuoteAttemptStatus.INVALID_RESPONSE:
            self._trigger_handoff(
                conversation, category="technical", reason=HandoffReasonTechnical.INVALID_QUOTE_SERVICE_RESPONSE
            )
            return

        # FAILED_TRANSIENT_EXHAUSTED
        self._trigger_handoff(
            conversation, category="technical", reason=HandoffReasonTechnical.QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES
        )

    # --- field-attempt tracking ------------------------------------------------

    def _current_pending_field(self, conversation: Conversation) -> RequiredField | None:
        missing = conversation.lead_profile.missing_required_fields()
        return missing[0] if missing else None

    def _check_field_attempts(self, conversation: Conversation, pending_before: RequiredField | None) -> None:
        if pending_before is None:
            return
        missing_now = conversation.lead_profile.missing_required_fields()
        if pending_before not in missing_now:
            conversation.lead_profile.field_attempts[pending_before] = 0
            return

        attempts = conversation.lead_profile.attempts_for(pending_before) + 1
        conversation.lead_profile.field_attempts[pending_before] = attempts
        if attempts >= self._settings.max_field_attempts:
            self._trigger_handoff(
                conversation,
                category="business",
                reason=HandoffReasonBusiness.REQUIRED_INFORMATION_CANNOT_BE_CONFIRMED,
            )

    # --- LLM call wrapper --------------------------------------------------------

    async def _call_llm_safely(
        self, conversation: Conversation, messages: list[LLMMessage], tools: list[ToolSpec]
    ) -> LLMToolResult | None:
        try:
            result = await self._llm_client.complete(messages, tools)
        except Exception as exc:  # noqa: BLE001 — the must-never-crash boundary
            conversation.llm_failure_count += 1
            logger.error(
                "llm.call.failed",
                conversation_id=conversation.id,
                consecutive_failures=conversation.llm_failure_count,
                exc_info=exc,
            )
            if conversation.llm_failure_count >= 2:
                self._trigger_handoff(
                    conversation, category="technical", reason=HandoffReasonTechnical.UNRECOVERABLE_INTEGRATION_FAILURE
                )
            else:
                self._append(
                    conversation,
                    MessageRole.AGENT,
                    MessageKind.TEXT,
                    "Desculpa, tive um problema técnico agora. Pode repetir sua última mensagem?",
                )
            return None

        conversation.llm_failure_count = 0
        return result

    # --- message construction / guardrails ---------------------------------------

    def _build_base_messages(self, conversation: Conversation) -> list[LLMMessage]:
        system_prompt = build_system_prompt(self._plans_catalog) + self._profile_state_note(conversation)
        history = [
            LLMMessage(role="user" if msg.role == MessageRole.LEAD else "assistant", content=msg.body)
            for msg in conversation.messages
            if msg.role == MessageRole.LEAD
            or (msg.role == MessageRole.AGENT and msg.kind in (MessageKind.TEXT, MessageKind.QUOTE))
        ]
        return [LLMMessage(role="system", content=system_prompt)] + history

    @staticmethod
    def _profile_state_note(conversation: Conversation) -> str:
        profile = conversation.lead_profile
        return (
            "\n\nEstado atual conhecido do lead (fonte de verdade — não pergunte de novo o que já está aqui): "
            f"veiculo_ano={profile.veiculo_ano if profile.veiculo_ano is not None else 'desconhecido'}, "
            f"idade={profile.idade if profile.idade is not None else 'desconhecida'}, "
            f"cep={profile.cep or 'não informado'}, "
            f"plano_id={profile.plano_id.value if profile.plano_id else 'não definido'}."
        )

    def _sanitize_llm_reply(self, text: str) -> str:
        if _looks_like_a_price_mention(text):
            logger.warning("llm_output_anomaly", reason="price_mention_without_successful_quote")
            return _FABRICATION_FALLBACK
        return text

    def _trigger_handoff(
        self,
        conversation: Conversation,
        *,
        category: Literal["technical", "business"],
        reason: HandoffReason,
        refusal_reason: str | None = None,
        last_lead_message: str | None = None,
    ) -> None:
        last_message = last_lead_message or self._last_lead_message(conversation)
        record = create_handoff_record(
            conversation,
            category=category,
            reason=reason,
            refusal_reason=refusal_reason,
            last_lead_message=last_message,
        )
        conversation.handoff = record
        conversation.status = ConversationStatus.HANDED_OFF
        self._append(conversation, MessageRole.AGENT, MessageKind.HANDOFF, record.user_message)
        logger.info(
            "handoff.triggered",
            conversation_id=conversation.id,
            handoff_id=record.id,
            category=category,
            reason=reason.value,
        )

    @staticmethod
    def _last_lead_message(conversation: Conversation) -> str | None:
        for msg in reversed(conversation.messages):
            if msg.role == MessageRole.LEAD:
                return msg.body
        return None

    @staticmethod
    def _append(
        conversation: Conversation,
        role: MessageRole,
        kind: MessageKind,
        body: str,
        *,
        quote_summary: QuoteSummary | None = None,
    ) -> Message:
        message = Message(conversation_id=conversation.id, role=role, kind=kind, body=body, quote_summary=quote_summary)
        conversation.messages.append(message)
        return message
