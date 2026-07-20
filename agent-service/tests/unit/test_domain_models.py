from app.domain.models import LeadProfile, PlanoId, RequiredField


def test_missing_required_fields_excludes_soft_required_cep():
    profile = LeadProfile(veiculo_ano=2018, idade=35, plano_id=PlanoId.COMPLETO)
    assert profile.missing_required_fields() == []
    assert profile.is_ready_for_quote() is True


def test_missing_required_fields_reports_hard_required_fields_in_order():
    profile = LeadProfile()
    assert profile.missing_required_fields() == [
        RequiredField.VEHICLE_YEAR,
        RequiredField.AGE,
        RequiredField.PLAN,
    ]
    assert profile.is_ready_for_quote() is False


def test_attempts_for_defaults_to_zero():
    profile = LeadProfile()
    assert profile.attempts_for(RequiredField.AGE) == 0
    profile.field_attempts[RequiredField.AGE] = 1
    assert profile.attempts_for(RequiredField.AGE) == 1
