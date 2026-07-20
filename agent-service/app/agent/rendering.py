"""Renders the lead-facing quote message and summary.

This is the structural guarantee behind "never invent a price": the text
and numbers shown to the lead are always built here, directly from a typed
QuoteResult that came from a successful quote-service call — never from
LLM-generated tokens. The LLM has no path to author this message.
"""
from __future__ import annotations

from app.domain.models import QuoteResult, QuoteSummary


def to_quote_summary(result: QuoteResult) -> QuoteSummary:
    return QuoteSummary(
        plano_id=result.plano_id,
        plano_nome=result.plano_nome,
        premio_mensal=result.premio_mensal,
        franquia=result.franquia,
        coberturas=result.coberturas,
        carencia_dias=result.carencia.dias,
        moeda=result.moeda,
    )


def render_quote_message(result: QuoteResult) -> str:
    coberturas = ", ".join(result.coberturas)
    carencia_coberturas = ", ".join(result.carencia.coberturas) or coberturas
    message = (
        f"Consegui sua cotação no plano {result.plano_nome}! "
        f"{result.moeda} {result.premio_mensal:.2f}/mês, franquia de {result.moeda} {result.franquia:.2f}. "
        f"Coberturas: {coberturas}. "
        f"Carência de {result.carencia.dias} dias para {carencia_coberturas}."
    )
    if result.primeiro_pagamento_pro_rata:
        pro_rata = result.primeiro_pagamento_pro_rata
        message += (
            f" Primeiro pagamento proporcional: {result.moeda} {pro_rata.valor_primeiro_pagamento:.2f} "
            f"({pro_rata.dias_cobrados} de {pro_rata.dias_no_mes} dias do mês)."
        )
    return message
