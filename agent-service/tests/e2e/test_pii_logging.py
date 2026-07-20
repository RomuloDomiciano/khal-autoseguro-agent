"""Confirms that when a lead volunteers PII-shaped text (CPF, phone) in a
free-text message, it never appears raw in the structured logs — only safe
metadata (conversation_id, message_type, char_len) is logged for the
message itself, and any handoff summary that quotes the lead's words has
already been redacted.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent.orchestrator import ConversationOrchestrator
from app.config.settings import Settings
from app.domain.repository import InMemoryConversationRepository
from app.integrations.quote_service.client import HttpxQuoteServiceClient
from app.main import app
from tests.fakes.fake_llm_client import FakeLLMClient
from tests.unit.test_orchestrator import _tool_result


def test_pii_in_lead_message_never_appears_raw_in_logs(quote_service_factory, capsys):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    settings = Settings(quote_service_base_url=base_url)
    app.state.orchestrator = ConversationOrchestrator(
        llm_client=FakeLLMClient([_tool_result("record_lead_info", {"requests_human": True})]),
        quote_client=HttpxQuoteServiceClient(settings),
        repository=InMemoryConversationRepository(),
        settings=settings,
    )
    client = TestClient(app)

    conversation_id = client.post("/api/v1/conversations").json()["conversationId"]
    cpf = "123.456.789-01"
    phone = "(11) 98888-7777"
    message_body = f"meu cpf é {cpf} e meu telefone é {phone}, quero falar com um atendente"

    response = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"body": message_body})
    assert response.json()["status"] == "handed_off"

    captured = capsys.readouterr()
    assert cpf not in captured.out
    assert phone not in captured.out
    assert "message.received" in captured.out
    assert "handoff.triggered" in captured.out
