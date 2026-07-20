"""Orchestrator tests using FakeLLMClient and FakeQuoteServiceClient — no
network, no real quote-service. These exercise the tool-calling loop's
deterministic guardrails: the price-fabrication guard is arguably the single
most important test in the suite (test 2 below).
"""
from __future__ import annotations

import pytest

from app.agent.orchestrator import _FABRICATION_FALLBACK, ConversationOrchestrator
from app.config.settings import Settings
from app.domain.models import (
    CarenciaInfo,
    Conversation,
    ConversationStatus,
    HandoffReasonBusiness,
    HandoffReasonTechnical,
    MessageKind,
    PlanoId,
    QuoteAttempt,
    QuoteAttemptStatus,
    QuoteRequestPayload,
    QuoteResult,
)
from app.domain.repository import InMemoryConversationRepository
from app.integrations.llm.base import LLMMessage, LLMToolCall, LLMToolResult
from app.integrations.quote_service.client import QuoteServiceOutcome
from tests.fakes.fake_llm_client import FakeLLMClient
from tests.fakes.fake_quote_service_client import FakeQuoteServiceClient


def _tool_result(name: str, arguments: dict, call_id: str = "call_1") -> LLMToolResult:
    return LLMToolResult(
        finish_reason="tool_calls",
        message=LLMMessage(role="assistant", tool_calls=[LLMToolCall(id=call_id, name=name, arguments=arguments)]),
    )


def _text_result(text: str) -> LLMToolResult:
    return LLMToolResult(finish_reason="stop", message=LLMMessage(role="assistant", content=text))


def _quote_result(**overrides) -> QuoteResult:
    defaults = dict(
        plano_id=PlanoId.COMPLETO,
        plano_nome="Completo",
        premio_mensal=209.90,
        franquia=3000.0,
        coberturas=["colisao", "roubo", "furto", "terceiros", "vidros"],
        multiplicadores={"faixa_etaria": 1.0, "idade_veiculo": 1.15, "regiao": 1.0},
        carencia=CarenciaInfo(coberturas=["roubo", "furto"], dias=30, observacao="..."),
        moeda="BRL",
    )
    defaults.update(overrides)
    return QuoteResult(**defaults)


def _success_outcome(result: QuoteResult) -> QuoteServiceOutcome:
    attempt = QuoteAttempt(
        conversation_id="conv_x",
        quote_request_id="qreq_x",
        attempt_number=1,
        status=QuoteAttemptStatus.SUCCEEDED,
        request_payload=QuoteRequestPayload(plano_id=result.plano_id, idade=35, veiculo_ano=2018),
        result=result,
    )
    return QuoteServiceOutcome(attempts=[attempt], final_status=QuoteAttemptStatus.SUCCEEDED, result=result)


async def _new_conversation(repo: InMemoryConversationRepository) -> Conversation:
    conversation = Conversation()
    await repo.create(conversation)
    return conversation


def _orchestrator(repo, llm_responses, quote_outcomes) -> ConversationOrchestrator:
    return ConversationOrchestrator(
        llm_client=FakeLLMClient(llm_responses),
        quote_client=FakeQuoteServiceClient(quote_outcomes),
        repository=repo,
        settings=Settings(max_tool_iterations=4, max_field_attempts=2),
    )


@pytest.mark.asyncio
async def test_happy_path_extraction_then_quote_success():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    quote_result = _quote_result()
    orchestrator = _orchestrator(
        repo,
        llm_responses=[
            _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
            _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
        ],
        quote_outcomes=[_success_outcome(quote_result)],
    )

    messages = await orchestrator.handle_message(conversation.id, "Corolla 2018, 35 anos, quero o completo")

    assert messages[-1].kind == MessageKind.QUOTE
    assert messages[-1].quote_summary.premio_mensal == quote_result.premio_mensal
    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.RESOLVED
    assert len(saved.quote_attempts) == 1
    assert saved.quote_attempts[0].quote_id is not None


@pytest.mark.asyncio
async def test_llm_answering_with_a_price_without_calling_the_tool_is_sanitized():
    """The core anti-fabrication guardrail: even if the model tries to state
    a price directly in plain text without ever calling get_quote, the lead
    never sees it and no quote attempt is recorded."""
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(
        repo,
        llm_responses=[_text_result("Show! Vai custar R$ 100 por mês, fechado?")],
        quote_outcomes=[],
    )

    messages = await orchestrator.handle_message(conversation.id, "quanto custa?")

    assert messages[-1].body == _FABRICATION_FALLBACK
    assert "R$" not in messages[-1].body
    saved = await repo.get(conversation.id)
    assert saved.quote_attempts == []


@pytest.mark.asyncio
async def test_get_quote_arg_mismatch_twice_triggers_conversation_state_inconsistent():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(
        repo,
        llm_responses=[
            _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}, call_id="call_1"),
            _tool_result("get_quote", {"plano_id": "premium", "idade": 40, "veiculo_ano": 2020}, call_id="call_2"),
        ],
        quote_outcomes=[],  # never actually executed — both are rejected as mismatches
    )

    await orchestrator.handle_message(conversation.id, "me dá uma cotação")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.HANDED_OFF
    assert saved.handoff.category == "technical"
    assert saved.handoff.reason == HandoffReasonTechnical.CONVERSATION_STATE_INCONSISTENT


@pytest.mark.asyncio
async def test_loop_exhaustion_triggers_low_confidence_handoff():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(
        repo,
        llm_responses=[
            _tool_result("record_lead_info", {"veiculo_ano": 2018}, call_id="c1"),
            _tool_result("record_lead_info", {"idade": 35}, call_id="c2"),
            _tool_result("record_lead_info", {"cep": "01310-100"}, call_id="c3"),
            _tool_result("record_lead_info", {"plano_id": "completo"}, call_id="c4"),
        ],
        quote_outcomes=[],
    )

    await orchestrator.handle_message(conversation.id, "vou te passando os dados aos poucos")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.HANDED_OFF
    assert saved.handoff.category == "business"
    assert saved.handoff.reason == HandoffReasonBusiness.AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD


@pytest.mark.asyncio
async def test_requests_human_flag_from_llm_triggers_handoff():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(
        repo,
        llm_responses=[_tool_result("record_lead_info", {"requests_human": True})],
        quote_outcomes=[],
    )

    await orchestrator.handle_message(conversation.id, "prefiro falar com uma pessoa de verdade sobre isso")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.HANDED_OFF
    assert saved.handoff.category == "business"
    assert saved.handoff.reason == HandoffReasonBusiness.LEAD_REQUESTS_HUMAN


@pytest.mark.asyncio
async def test_field_attempt_exhaustion_triggers_handoff():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(
        repo,
        llm_responses=[
            _tool_result("record_lead_info", {"idade": 35}, call_id="c1"),  # never fills veiculo_ano (pending)
            _tool_result("record_lead_info", {"cep": "01310-100"}, call_id="c2"),  # still doesn't fill it
        ],
        quote_outcomes=[],
    )

    await orchestrator.handle_message(conversation.id, "não lembro o ano do carro")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.HANDED_OFF
    assert saved.handoff.reason == HandoffReasonBusiness.REQUIRED_INFORMATION_CANNOT_BE_CONFIRMED


@pytest.mark.asyncio
async def test_keyword_fast_path_skips_the_llm_entirely():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    llm_client = FakeLLMClient([])  # would raise if ever called
    orchestrator = ConversationOrchestrator(
        llm_client=llm_client,
        quote_client=FakeQuoteServiceClient([]),
        repository=repo,
        settings=Settings(),
    )

    await orchestrator.handle_message(conversation.id, "quero falar com um atendente")

    assert llm_client.calls == []
    saved = await repo.get(conversation.id)
    assert saved.handoff.reason == HandoffReasonBusiness.LEAD_REQUESTS_HUMAN


@pytest.mark.asyncio
async def test_handed_off_conversation_gives_canned_reply_with_no_llm_call():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    conversation.status = ConversationStatus.HANDED_OFF
    await repo.save(conversation)
    llm_client = FakeLLMClient([])
    orchestrator = ConversationOrchestrator(
        llm_client=llm_client,
        quote_client=FakeQuoteServiceClient([]),
        repository=repo,
        settings=Settings(),
    )

    messages = await orchestrator.handle_message(conversation.id, "ainda está aí?")

    assert llm_client.calls == []
    assert "atendente" in messages[-1].body.lower()


@pytest.mark.asyncio
async def test_single_llm_failure_gives_canned_retry_and_stays_collecting():
    def _boom(_messages, _tools):
        raise RuntimeError("simulated LLM outage")

    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(repo, llm_responses=[_boom], quote_outcomes=[])

    await orchestrator.handle_message(conversation.id, "oi")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.COLLECTING
    assert saved.llm_failure_count == 1


@pytest.mark.asyncio
async def test_two_consecutive_llm_failures_trigger_technical_handoff():
    def _boom(_messages, _tools):
        raise RuntimeError("simulated LLM outage")

    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = _orchestrator(repo, llm_responses=[_boom, _boom], quote_outcomes=[])

    await orchestrator.handle_message(conversation.id, "oi")
    await orchestrator.handle_message(conversation.id, "alo?")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.HANDED_OFF
    assert saved.handoff.reason == HandoffReasonTechnical.UNRECOVERABLE_INTEGRATION_FAILURE
