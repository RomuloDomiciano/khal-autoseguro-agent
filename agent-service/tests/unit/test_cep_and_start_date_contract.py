"""Makes explicit, as a named contract rather than an incidental side
effect of other fixtures, that CEP is soft-required: the agent may ask for
it, but a quote must still resolve successfully if the lead never provides
one. This mirrors quote-service's own contract (a missing CEP means a
region multiplier of 1.0, not a refusal) — see agent-service/README.md's
"Decisions, and why" section for the full reasoning, and
domain/models.py's SOFT_REQUIRED_FIELDS.

Also proves the data_inicio contract: the LLM has no channel to record a
start date (record_lead_info has no such field, LeadProfile has no such
field) and get_quote's tool spec has no data_inicio parameter, so even a
non-conformant model response that includes one is silently dropped before
it ever reaches quote-service — see app/agent/tools.py.
"""
import pytest

from app.agent.orchestrator import ConversationOrchestrator
from app.config.settings import Settings
from app.domain.models import ConversationStatus, RequiredField, SOFT_REQUIRED_FIELDS
from app.domain.repository import InMemoryConversationRepository
from tests.fakes.fake_llm_client import FakeLLMClient
from tests.fakes.fake_quote_service_client import FakeQuoteServiceClient
from tests.unit.test_orchestrator import _new_conversation, _quote_result, _success_outcome, _tool_result


def test_cep_is_the_only_soft_required_field():
    assert SOFT_REQUIRED_FIELDS == frozenset({RequiredField.CEP})


@pytest.mark.asyncio
async def test_quote_resolves_successfully_even_though_cep_was_never_provided():
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    quote_result = _quote_result()
    orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient(
            [
                # No cep anywhere in this turn's extraction.
                _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
                _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
            ]
        ),
        quote_client=FakeQuoteServiceClient([_success_outcome(quote_result)]),
        repository=repo,
        settings=Settings(max_tool_iterations=4, max_field_attempts=2),
    )

    await orchestrator.handle_message(conversation.id, "Corolla 2018, 35 anos, completo, sem CEP mesmo")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.RESOLVED
    assert saved.lead_profile.cep is None
    # Never handed off for a missing CEP, and never counted as a failed
    # attempt against any field.
    assert saved.lead_profile.field_attempts.get(RequiredField.CEP, 0) == 0


@pytest.mark.asyncio
async def test_llm_supplied_data_inicio_never_reaches_the_quote_request():
    """The model has no confirmed conversation state to supply a start
    date from (no extraction field, no LeadProfile field), so even if a
    non-conformant tool call includes one, it must not affect the price
    quoted to the lead."""
    repo = InMemoryConversationRepository()
    conversation = await _new_conversation(repo)
    quote_result = _quote_result()
    quote_client = FakeQuoteServiceClient([_success_outcome(quote_result)])
    orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient(
            [
                _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
                _tool_result(
                    "get_quote",
                    {
                        "plano_id": "completo",
                        "idade": 35,
                        "veiculo_ano": 2018,
                        # Not a real get_quote parameter — simulates a model
                        # that tries to invent a start date anyway.
                        "data_inicio": "2020-01-01",
                    },
                ),
            ]
        ),
        quote_client=quote_client,
        repository=repo,
        settings=Settings(max_tool_iterations=4, max_field_attempts=2),
    )

    await orchestrator.handle_message(conversation.id, "Corolla 2018, 35 anos, completo")

    saved = await repo.get(conversation.id)
    assert saved.status == ConversationStatus.RESOLVED
    assert len(quote_client.calls) == 1
    assert quote_client.calls[0].data_inicio is None
