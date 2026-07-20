"""End-to-end tests: real FastAPI app (TestClient) + FakeLLMClient (no real
OpenAI call, no cost, fully deterministic) + the real quote-service running
as a subprocess with controlled instability. This is the closest thing to
the actual deployed request path short of a live LLM.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agent.orchestrator import ConversationOrchestrator
from app.config.settings import Settings
from app.domain.repository import InMemoryConversationRepository
from app.integrations.quote_service.client import HttpxQuoteServiceClient
from app.main import app
from tests.fakes.fake_llm_client import FakeLLMClient
from tests.unit.test_orchestrator import _tool_result


def _make_client(base_url: str, llm_responses: list) -> TestClient:
    settings = Settings(quote_service_base_url=base_url, max_tool_iterations=4, max_field_attempts=2)
    app.state.orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient(llm_responses),
        quote_client=HttpxQuoteServiceClient(settings),
        repository=InMemoryConversationRepository(),
        settings=settings,
    )
    return TestClient(app)


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_happy_path_end_to_end_returns_resolved_status_and_quote(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = _make_client(
        base_url,
        llm_responses=[
            _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
            _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
        ],
    )

    create_response = client.post("/api/v1/conversations")
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversationId"]

    message_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "Corolla 2018, 35 anos, plano completo"},
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert body["status"] == "resolved"
    assert body["messages"][-1]["kind"] == "quote"
    assert body["messages"][-1]["quoteSummary"]["premioMensal"] > 0

    state_response = client.get(f"/api/v1/conversations/{conversation_id}")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["status"] == "resolved"
    assert len(state["quoteAttempts"]) == 1
    assert state["quoteAttempts"][0]["status"] == "succeeded"


def test_forced_quote_service_failure_hands_off_without_a_price_anywhere(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="1.0", QUOTE_SLOW_RATE="0.0", QUOTE_SEED="7")
    client = _make_client(
        base_url,
        llm_responses=[
            _tool_result("record_lead_info", {"veiculo_ano": 2018, "idade": 35, "plano_id": "completo"}),
            _tool_result("get_quote", {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018}),
        ],
    )

    conversation_id = client.post("/api/v1/conversations").json()["conversationId"]
    message_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "Corolla 2018, 35 anos, plano completo"},
    )

    body = message_response.json()
    assert body["status"] == "handed_off"
    assert body["messages"][-1]["kind"] == "handoff"
    response_text = message_response.text
    assert "R$" not in response_text  # no price anywhere in the response

    attempts_response = client.get(f"/api/v1/conversations/{conversation_id}/quote-attempts")
    attempts = attempts_response.json()
    assert len(attempts) == 3  # max_attempts default
    assert [a["attemptNumber"] for a in attempts] == [1, 2, 3]
    # API trace must be consistent with the domain outcome: earlier
    # attempts were retried, the final one is what actually exhausted the
    # budget — not still "retrying" with nothing left to retry.
    assert [a["status"] for a in attempts] == ["retrying", "retrying", "failed_transient_exhausted"]

    state = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert state["handoff"]["reason"] == "quote_service_unavailable_after_retries"
    # Summary is exposed for the human operator, and never mentions a price.
    assert state["handoff"]["summary"]
    assert "R$" not in state["handoff"]["summary"]


def test_unknown_conversation_id_returns_404(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = _make_client(base_url, llm_responses=[])

    response = client.post(
        "/api/v1/conversations/conv_does_not_exist/messages", json={"body": "oi"}
    )
    assert response.status_code == 404


def test_two_failed_attempts_on_the_same_field_hand_off(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = _make_client(
        base_url,
        llm_responses=[
            _tool_result("record_lead_info", {"idade": 35}, call_id="c1"),
            _tool_result("record_lead_info", {"cep": "01310-100"}, call_id="c2"),
        ],
    )

    conversation_id = client.post("/api/v1/conversations").json()["conversationId"]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages", json={"body": "não sei o ano do carro"}
    )

    body = response.json()
    assert body["status"] == "handed_off"
    state = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert state["handoff"]["reason"] == "required_information_cannot_be_confirmed"
