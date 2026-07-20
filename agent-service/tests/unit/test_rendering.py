from app.agent.rendering import render_quote_message, to_quote_summary
from app.domain.models import CarenciaInfo, PlanoId, ProRataInfo, QuoteResult


def _result(**overrides) -> QuoteResult:
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


def test_render_quote_message_contains_exact_price_from_result():
    message = render_quote_message(_result())
    assert "209.90" in message
    assert "3000.00" in message
    assert "Completo" in message
    assert "30 dias" in message


def test_render_quote_message_includes_pro_rata_when_present():
    result = _result(
        primeiro_pagamento_pro_rata=ProRataInfo(dias_no_mes=31, dias_cobrados=17, valor_primeiro_pagamento=115.15)
    )
    message = render_quote_message(result)
    assert "115.15" in message
    assert "17 de 31 dias" in message


def test_render_quote_message_omits_pro_rata_when_absent():
    message = render_quote_message(_result())
    assert "proporcional" not in message


def test_to_quote_summary_maps_fields_exactly():
    result = _result()
    summary = to_quote_summary(result)
    assert summary.plano_id == PlanoId.COMPLETO
    assert summary.premio_mensal == 209.90
    assert summary.franquia == 3000.0
    assert summary.carencia_dias == 30
    assert summary.moeda == "BRL"
    assert summary.coberturas == result.coberturas
