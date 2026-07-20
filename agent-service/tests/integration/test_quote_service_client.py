"""Integration tests against the real (unmodified) quote-service, made
deterministic via its QUOTE_SEED/QUOTE_FAILURE_RATE/QUOTE_SLOW_RATE env vars.
These exercise the branch main.py's plan called out as the single biggest
differentiator: what the agent does when /quote fails, and whether a
slow-but-successful call is ever misclassified as a failure.
"""
from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.domain.models import ErrorClass, PlanoId, QuoteAttemptStatus, QuoteRequestPayload
from app.integrations.quote_service.client import HttpxQuoteServiceClient


def _fast_settings(base_url: str, **overrides) -> Settings:
    """Test settings with tiny backoff so exhaustion tests run in
    milliseconds instead of seconds, and env vars uninvolved in the assertion
    left at their defaults."""
    defaults = dict(
        quote_service_base_url=base_url,
        quote_service_connect_timeout_seconds=3.0,
        quote_service_read_timeout_seconds=15.0,
        quote_service_max_attempts=3,
        quote_service_backoff_base_seconds=0.02,
        quote_service_backoff_multiplier=2.0,
        quote_service_backoff_max_seconds=0.1,
        quote_service_backoff_jitter=0.1,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_forced_failure_exhausts_retries_without_fabricating_a_price(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="1.0", QUOTE_SLOW_RATE="0.0", QUOTE_SEED="42")
    client = HttpxQuoteServiceClient(_fast_settings(base_url))
    payload = QuoteRequestPayload(plano_id=PlanoId.COMPLETO, idade=35, veiculo_ano=2018, cep="01310-100")

    outcome = await client.request_quote(payload, conversation_id="conv_1", quote_request_id="qreq_1")

    assert outcome.final_status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
    assert outcome.result is None
    assert len(outcome.attempts) == 3
    for attempt in outcome.attempts:
        assert attempt.result is None
        assert attempt.error_class in {ErrorClass.HTTP_500, ErrorClass.HTTP_502, ErrorClass.HTTP_503}
        assert attempt.http_status in {500, 502, 503}
    # Earlier attempts were retried; the final one is what actually
    # exhausted the budget, so its own status must say so rather than
    # still claiming "retrying" after there was nothing left to retry.
    for attempt in outcome.attempts[:-1]:
        assert attempt.status == QuoteAttemptStatus.RETRYING
    assert outcome.attempts[-1].status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED


@pytest.mark.asyncio
async def test_slow_but_successful_call_is_not_misclassified_as_a_failure(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="1.0", QUOTE_SLOW_SECONDS="1")
    client = HttpxQuoteServiceClient(_fast_settings(base_url, quote_service_read_timeout_seconds=5.0))
    payload = QuoteRequestPayload(plano_id=PlanoId.ESSENCIAL, idade=35, veiculo_ano=2018, cep="01310-100")

    outcome = await client.request_quote(payload, conversation_id="conv_2", quote_request_id="qreq_2")

    assert outcome.final_status == QuoteAttemptStatus.SUCCEEDED
    assert outcome.result is not None
    assert outcome.result.plano_id == PlanoId.ESSENCIAL
    assert len(outcome.attempts) == 1
    assert outcome.attempts[0].latency_ms >= 900  # the ~1s simulated slowness actually happened


@pytest.mark.asyncio
async def test_read_timeout_shorter_than_slowness_is_classified_as_timeout_and_exhausts(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="1.0", QUOTE_SLOW_SECONDS="3")
    client = HttpxQuoteServiceClient(_fast_settings(base_url, quote_service_read_timeout_seconds=0.5))
    payload = QuoteRequestPayload(plano_id=PlanoId.ESSENCIAL, idade=35, veiculo_ano=2018)

    outcome = await client.request_quote(payload, conversation_id="conv_3", quote_request_id="qreq_3")

    assert outcome.final_status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
    assert outcome.result is None
    for attempt in outcome.attempts:
        assert attempt.error_class == ErrorClass.TIMEOUT
    for attempt in outcome.attempts[:-1]:
        assert attempt.status == QuoteAttemptStatus.RETRYING
    assert outcome.attempts[-1].status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED


@pytest.mark.asyncio
async def test_business_refusal_for_age_over_limit_is_not_retried(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = HttpxQuoteServiceClient(_fast_settings(base_url))
    payload = QuoteRequestPayload(plano_id=PlanoId.ESSENCIAL, idade=80, veiculo_ano=2018)

    outcome = await client.request_quote(payload, conversation_id="conv_4", quote_request_id="qreq_4")

    assert outcome.final_status == QuoteAttemptStatus.REFUSED
    assert outcome.result is None
    assert len(outcome.attempts) == 1  # never retried
    assert "75" in (outcome.refusal_reason or "")


@pytest.mark.asyncio
async def test_happy_path_succeeds_on_first_try_when_stable(quote_service_factory):
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = HttpxQuoteServiceClient(_fast_settings(base_url))
    payload = QuoteRequestPayload(plano_id=PlanoId.PREMIUM, idade=35, veiculo_ano=2020, cep="01310-100")

    outcome = await client.request_quote(payload, conversation_id="conv_5", quote_request_id="qreq_5")

    assert outcome.final_status == QuoteAttemptStatus.SUCCEEDED
    assert outcome.result is not None
    assert outcome.result.premio_mensal > 0
    assert len(outcome.attempts) == 1


@pytest.mark.asyncio
async def test_data_inicio_not_on_the_first_of_the_month_returns_pro_rata_from_quote_service(quote_service_factory):
    """data_inicio and its pro-rata math are entirely quote-service's
    responsibility. The agent itself never sets data_inicio on a quote
    request — see app/agent/tools.py::to_quote_request_payload and
    tests/unit/test_cep_and_start_date_contract.py — but QuoteRequestPayload
    mirrors quote-service's wire contract 1:1, so this proves the client's
    transport layer maps the field correctly against the real service."""
    base_url = quote_service_factory(QUOTE_FAILURE_RATE="0.0", QUOTE_SLOW_RATE="0.0")
    client = HttpxQuoteServiceClient(_fast_settings(base_url))
    payload = QuoteRequestPayload(
        plano_id=PlanoId.ESSENCIAL, idade=35, veiculo_ano=2018, data_inicio="2026-08-15"
    )

    outcome = await client.request_quote(payload, conversation_id="conv_6", quote_request_id="qreq_6")

    assert outcome.final_status == QuoteAttemptStatus.SUCCEEDED
    assert outcome.result is not None
    assert outcome.result.primeiro_pagamento_pro_rata is not None
    assert outcome.result.primeiro_pagamento_pro_rata.dias_cobrados < outcome.result.primeiro_pagamento_pro_rata.dias_no_mes


@pytest.mark.asyncio
async def test_http_500_with_unrelated_body_is_not_retried(httpx_mock):
    """This project's quote-service only ever emits 500 with the
    {"error": "upstream_unavailable"} envelope for its simulated
    instability (see test_forced_failure_exhausts_retries_without_fabricating_a_price,
    which exercises that real, retryable path). A 500 with any other body
    is not a shape we recognize as that known transient failure, so it must
    not be silently retried three times against what could be a genuinely
    different failure — mocked here since the real quote-service cannot be
    made to emit a malformed body on demand."""
    httpx_mock.add_response(
        method="POST", url="http://fake-quote-service/quote", status_code=500, json={"detail": "boom"}
    )
    client = HttpxQuoteServiceClient(_fast_settings("http://fake-quote-service"))
    payload = QuoteRequestPayload(plano_id=PlanoId.COMPLETO, idade=35, veiculo_ano=2018, cep="01310-100")

    outcome = await client.request_quote(payload, conversation_id="conv_7", quote_request_id="qreq_7")

    assert outcome.final_status == QuoteAttemptStatus.REJECTED_INVALID
    assert outcome.result is None
    assert len(outcome.attempts) == 1  # never retried
    assert outcome.attempts[0].http_status == 500
    assert outcome.attempts[0].error_class == ErrorClass.INVALID_RESPONSE_CONTRACT
    assert outcome.attempts[0].status == QuoteAttemptStatus.REJECTED_INVALID


@pytest.mark.asyncio
async def test_http_500_with_known_transient_envelope_is_retried(httpx_mock):
    """Mirror of the malformed-body case above: the documented envelope
    must still be retried, mocked here for a fast, deterministic unit-level
    check of the same behavior the real-quote-service test proves end to
    end."""
    for _ in range(3):
        httpx_mock.add_response(
            method="POST",
            url="http://fake-quote-service/quote",
            status_code=500,
            json={"error": "upstream_unavailable"},
        )
    client = HttpxQuoteServiceClient(_fast_settings("http://fake-quote-service"))
    payload = QuoteRequestPayload(plano_id=PlanoId.COMPLETO, idade=35, veiculo_ano=2018, cep="01310-100")

    outcome = await client.request_quote(payload, conversation_id="conv_8", quote_request_id="qreq_8")

    assert outcome.final_status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
    assert len(outcome.attempts) == 3
    assert all(a.error_class == ErrorClass.HTTP_500 for a in outcome.attempts)
    assert outcome.attempts[-1].status == QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
