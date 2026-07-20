"""Focused tests for the plain-text price-fabrication safety net
(_looks_like_a_price_mention / _sanitize_llm_reply). This is explicitly the
belt-and-suspenders layer, not the primary guarantee — the primary guarantee
is structural (see test_orchestrator.py's
test_llm_answering_with_a_price_without_calling_the_tool_is_sanitized and
test_rendering.py's deterministic-template tests).
"""
import pytest

from app.agent.orchestrator import (
    _FABRICATION_FALLBACK,
    ConversationOrchestrator,
    _looks_like_a_price_mention,
)
from app.config.settings import Settings
from app.domain.repository import InMemoryConversationRepository
from tests.fakes.fake_llm_client import FakeLLMClient
from tests.fakes.fake_quote_service_client import FakeQuoteServiceClient
from tests.unit.test_orchestrator import _new_conversation, _quote_result, _success_outcome, _text_result, _tool_result


@pytest.mark.parametrize(
    "text",
    [
        "Vai custar R$ 199 por mês.",
        "Fica R$199,90/mês.",
        "O valor é BRL 199 por mês.",
        "São 199 reais por mês.",
        "Fica 199,90 reais.",
        "O valor é 199 por mês.",
        "Sai por 199/mês.",
        "Sai por 199 /mês.",
        "A mensalidade de 199 já está confirmada.",
    ],
)
def test_flags_every_supported_price_format(text):
    assert _looks_like_a_price_mention(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Seu carro é um Corolla 2018.",  # vehicle year
        "Você tem 35 anos, certo?",  # age
        "Seu CEP é 01310-100.",  # CEP
        "O identificador da conversa é conv_e7220b51a6ab.",  # conversation id
        "A cotação qte_1a2b3c4d já foi registrada.",  # quote id
        "Faltam 2 tentativas para esse campo.",  # unrelated small number
        "Vou calcular seu prêmio agora, só um instante.",  # mentions premium, no number
    ],
)
def test_does_not_flag_ordinary_non_price_numbers(text):
    assert _looks_like_a_price_mention(text) is False


@pytest.mark.asyncio
async def test_successful_quote_rendering_is_never_sanitized():
    """The deterministic template output (which legitimately contains
    'BRL <number>') must reach the lead unmodified — the guard only applies
    to LLM-authored free text, never to render_quote_message's output."""
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    quote_result = _quote_result()
    orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient(
            [
                _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
                _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
            ]
        ),
        quote_client=FakeQuoteServiceClient([_success_outcome(quote_result)]),
        repository=repo,
        settings=Settings(max_tool_iterations=4, max_field_attempts=2),
    )

    messages = await orchestrator.handle_message(conversation.id, "Corolla 2018, 35 anos, completo")

    assert messages[-1].kind.value == "quote"
    assert str(quote_result.premio_mensal) in messages[-1].body
    assert messages[-1].body != _FABRICATION_FALLBACK


@pytest.mark.asyncio
async def test_price_mention_in_plain_text_without_any_tool_call_is_sanitized():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient([_text_result("Fica 199,90 reais por mês, fechado?")]),
        quote_client=FakeQuoteServiceClient([]),
        repository=repo,
        settings=Settings(),
    )

    messages = await orchestrator.handle_message(conversation.id, "quanto custa?")

    assert messages[-1].body == _FABRICATION_FALLBACK


@pytest.mark.asyncio
async def test_price_mention_after_a_rejected_get_quote_call_is_still_sanitized():
    """Even after the model's get_quote call is rejected (arg mismatch, not
    yet a terminal handoff), a subsequent plain-text price claim in the same
    turn must still be caught."""
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient(
            [
                _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
                _text_result("Tudo bem, fica BRL 199 por mês mesmo assim."),
            ]
        ),
        quote_client=FakeQuoteServiceClient([]),
        repository=repo,
        settings=Settings(max_tool_iterations=4),
    )

    messages = await orchestrator.handle_message(conversation.id, "me dá uma cotação")

    assert messages[-1].body == _FABRICATION_FALLBACK
