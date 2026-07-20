from app.observability.redact import redact_cep, redact_pii


def test_redact_pii_scrubs_cpf():
    assert "123.456.789-01" not in redact_pii("meu cpf é 123.456.789-01")
    assert "[cpf]" in redact_pii("meu cpf é 123.456.789-01")


def test_redact_pii_scrubs_email():
    text = redact_pii("pode me chamar em teste@example.com")
    assert "teste@example.com" not in text
    assert "[email]" in text


def test_redact_pii_scrubs_phone():
    text = redact_pii("meu telefone é (11) 98888-7777")
    assert "98888-7777" not in text
    assert "[telefone]" in text


def test_redact_pii_scrubs_plate():
    text = redact_pii("a placa é ABC1D23")
    assert "ABC1D23" not in text
    assert "[placa]" in text


def test_redact_pii_leaves_unrelated_text_untouched():
    text = "meu carro é um Corolla 2018 e tenho 35 anos"
    assert redact_pii(text) == text


def test_redact_cep_truncates_to_two_digit_prefix():
    assert redact_cep("01310-100") == "01"
    assert redact_cep("07123-456") == "07"


def test_redact_cep_handles_none():
    assert redact_cep(None) is None
