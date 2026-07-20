import pytest

from app.agent.policies.handoff_policy import (
    create_handoff_record,
    detect_human_request_keywords,
    render_summary,
    render_user_message,
)
from app.domain.models import (
    Conversation,
    HandoffReasonBusiness,
    HandoffReasonTechnical,
    LeadProfile,
    PlanoId,
)


@pytest.mark.parametrize(
    "reason",
    [
        HandoffReasonTechnical.QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES,
        HandoffReasonTechnical.INVALID_QUOTE_SERVICE_RESPONSE,
        HandoffReasonTechnical.UNRECOVERABLE_INTEGRATION_FAILURE,
        HandoffReasonTechnical.CONVERSATION_STATE_INCONSISTENT,
        HandoffReasonBusiness.LEAD_REQUESTS_HUMAN,
        HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN,
        HandoffReasonBusiness.REQUIRED_INFORMATION_CANNOT_BE_CONFIRMED,
        HandoffReasonBusiness.AGENT_CONFIDENCE_BELOW_PROJECT_THRESHOLD,
        HandoffReasonBusiness.SCENARIO_OUTSIDE_SUPPORTED_SCOPE,
    ],
)
def test_every_reason_has_a_user_safe_message_with_no_raw_internals(reason):
    message = render_user_message(reason, refusal_reason="Idade acima do limite de aceitação (75 anos).")
    assert message
    # never leaks stack-trace / exception-shaped internals
    assert "Traceback" not in message
    assert "Exception" not in message
    assert "httpx" not in message.lower()


def test_unsupported_vehicle_or_plan_includes_the_quote_service_reason():
    message = render_user_message(
        HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN,
        refusal_reason="Veiculo com mais de 20 anos nao e aceito.",
    )
    assert "Veiculo com mais de 20 anos nao e aceito." in message


def test_create_handoff_record_sets_machine_readable_fields():
    conversation = Conversation(
        lead_profile=LeadProfile(veiculo_ano=1990, idade=35, cep="01310-100", plano_id=PlanoId.ESSENCIAL)
    )
    record = create_handoff_record(
        conversation,
        category="business",
        reason=HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN,
        refusal_reason="Veiculo com mais de 20 anos nao e aceito.",
        last_lead_message="meu carro é de 1990, meu cpf é 123.456.789-01",
    )
    assert record.conversation_id == conversation.id
    assert record.category == "business"
    assert record.reason == HandoffReasonBusiness.UNSUPPORTED_VEHICLE_OR_PLAN
    assert record.lead_profile_snapshot.veiculo_ano == 1990
    assert "Veiculo com mais de 20 anos" in record.user_message


def test_summary_redacts_pii_from_last_lead_message():
    conversation = Conversation(lead_profile=LeadProfile(idade=35))
    summary = render_summary(
        conversation,
        HandoffReasonBusiness.LEAD_REQUESTS_HUMAN,
        last_lead_message="me liga, meu cpf é 123.456.789-01 e email teste@example.com",
    )
    assert "123.456.789-01" not in summary
    assert "teste@example.com" not in summary
    assert "[cpf]" in summary
    assert "[email]" in summary


def test_summary_redacts_cep_to_its_two_digit_region_prefix():
    """render_summary must follow the same redaction policy as everywhere
    else CEP is exposed for observability: only the 2-digit region prefix,
    never the full value — see app/observability/redact.py::redact_cep."""
    conversation = Conversation(
        lead_profile=LeadProfile(veiculo_ano=2018, idade=35, cep="01310-100", plano_id=PlanoId.COMPLETO)
    )
    summary = render_summary(
        conversation, HandoffReasonTechnical.QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES, last_lead_message=None
    )
    assert "01310-100" not in summary
    assert "01310100" not in summary
    assert "01" in summary


def test_create_handoff_record_summary_never_contains_the_full_cep_but_snapshot_does():
    """The redaction applies to the human-facing summary text only — the
    operational lead_profile_snapshot must still carry the full CEP, since
    quoting legitimately needs it and nothing requires stripping it from
    internal state."""
    conversation = Conversation(
        lead_profile=LeadProfile(veiculo_ano=2018, idade=35, cep="01310-100", plano_id=PlanoId.COMPLETO)
    )
    record = create_handoff_record(
        conversation,
        category="technical",
        reason=HandoffReasonTechnical.QUOTE_SERVICE_UNAVAILABLE_AFTER_RETRIES,
    )
    assert "01310-100" not in record.summary
    assert record.lead_profile_snapshot.cep == "01310-100"


def test_summary_handles_missing_fields_gracefully():
    conversation = Conversation(lead_profile=LeadProfile())
    summary = render_summary(conversation, HandoffReasonBusiness.LEAD_REQUESTS_HUMAN, last_lead_message=None)
    assert "não informado" in summary or "não definido" in summary


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("quero falar com um atendente", True),
        ("me passa pra um humano por favor", True),
        ("preciso de um supervisor", True),
        ("meu carro é um Corolla 2018", False),
        ("tenho 35 anos", False),
    ],
)
def test_detect_human_request_keywords(text, expected):
    assert detect_human_request_keywords(text) is expected
