import pytest

from app.agent.tools import (
    GET_QUOTE,
    ToolArgumentError,
    apply_record_lead_info,
    get_quote_args_match_profile,
    parse_get_quote_args,
    parse_record_lead_info_args,
    to_quote_request_payload,
)
from app.domain.models import LeadProfile, PlanoId


def test_parse_record_lead_info_args_accepts_partial_fields():
    args = parse_record_lead_info_args({"veiculo_ano": 2018, "idade": 35})
    assert args.veiculo_ano == 2018
    assert args.idade == 35
    assert args.cep is None
    assert args.requests_human is False


def test_parse_record_lead_info_args_rejects_out_of_range_values():
    with pytest.raises(ToolArgumentError):
        parse_record_lead_info_args({"idade": 300})


def test_apply_record_lead_info_only_updates_provided_fields():
    profile = LeadProfile(veiculo_ano=2018)
    args = parse_record_lead_info_args({"idade": 35})
    updated = apply_record_lead_info(profile, args)
    assert updated.veiculo_ano == 2018  # untouched
    assert updated.idade == 35
    assert profile.idade is None  # original not mutated


def test_parse_get_quote_args_requires_mandatory_fields():
    with pytest.raises(ToolArgumentError):
        parse_get_quote_args({"plano_id": "completo"})  # missing idade/veiculo_ano


def test_get_quote_args_match_profile_true_when_identical():
    profile = LeadProfile(veiculo_ano=2018, idade=35, cep="01310-100", plano_id=PlanoId.COMPLETO)
    args = parse_get_quote_args({"plano_id": "completo", "idade": 35, "veiculo_ano": 2018, "cep": "01310-100"})
    assert get_quote_args_match_profile(args, profile) is True


def test_get_quote_args_match_profile_false_when_model_invents_a_different_value():
    profile = LeadProfile(veiculo_ano=2018, idade=35, plano_id=PlanoId.COMPLETO)
    tampered_args = parse_get_quote_args({"plano_id": "premium", "idade": 35, "veiculo_ano": 2018})
    assert get_quote_args_match_profile(tampered_args, profile) is False


def test_get_quote_args_match_profile_treats_empty_and_none_cep_as_equivalent():
    profile = LeadProfile(veiculo_ano=2018, idade=35, plano_id=PlanoId.COMPLETO, cep=None)
    args = parse_get_quote_args({"plano_id": "completo", "idade": 35, "veiculo_ano": 2018})
    assert get_quote_args_match_profile(args, profile) is True


def test_to_quote_request_payload_maps_fields_through():
    args = parse_get_quote_args({"plano_id": "premium", "idade": 40, "veiculo_ano": 2020, "cep": "07123-456"})
    payload = to_quote_request_payload(args)
    assert payload.plano_id == PlanoId.PREMIUM
    assert payload.idade == 40
    assert payload.veiculo_ano == 2020
    assert payload.cep == "07123-456"


def test_to_quote_request_payload_omits_cep_when_never_provided():
    """CEP is soft-required: quote-service treats a missing CEP as valid
    input (region multiplier defaults to 1.0), so the payload must be
    constructible and valid without it."""
    args = parse_get_quote_args({"plano_id": "essencial", "idade": 30, "veiculo_ano": 2015})
    payload = to_quote_request_payload(args)
    assert payload.cep is None


def test_get_quote_tool_spec_has_no_data_inicio_parameter():
    """data_inicio drives quote-service's pro-rata first-payment math, and
    there is no confirmed-profile value to validate it against, so it must
    not be an LLM-settable argument of get_quote — otherwise the model
    could silently pick the price shown to the lead."""
    assert "data_inicio" not in GET_QUOTE.parameters["properties"]


def test_parse_get_quote_args_ignores_a_data_inicio_argument_from_the_model():
    """Even if a non-conformant LLM response includes data_inicio anyway,
    parsing must silently drop it rather than let it reach the quote
    request."""
    args = parse_get_quote_args(
        {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018, "data_inicio": "2026-07-15"}
    )
    assert not hasattr(args, "data_inicio")


def test_to_quote_request_payload_data_inicio_always_none():
    """The agent never has a trustworthy source for data_inicio, so the
    quote request it builds must never carry one, regardless of what the
    model's tool-call arguments contained."""
    args = parse_get_quote_args(
        {"plano_id": "completo", "idade": 35, "veiculo_ano": 2018, "data_inicio": "2026-07-15"}
    )
    payload = to_quote_request_payload(args)
    assert payload.data_inicio is None
