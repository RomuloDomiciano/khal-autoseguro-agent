import random

import httpx
import pytest

from app.domain.models import ErrorClass
from app.domain.policies.retry_policy import (
    classify_response,
    classify_transport_exception,
    is_retryable,
    next_backoff_seconds,
)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ConnectError("boom"), ErrorClass.CONNECTION_ERROR),
        (httpx.ConnectTimeout("boom"), ErrorClass.TIMEOUT),
        (httpx.ReadTimeout("boom"), ErrorClass.TIMEOUT),
        (httpx.PoolTimeout("boom"), ErrorClass.TIMEOUT),
    ],
)
def test_classify_transport_exception(exc, expected):
    assert classify_transport_exception(exc) == expected


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (500, {"error": "upstream_unavailable"}, ErrorClass.HTTP_500),
        # Any 500 body other than the known transient envelope is not
        # something we can safely assume is retryable.
        (500, {"error": "something_else"}, ErrorClass.INVALID_RESPONSE_CONTRACT),
        (500, {"detail": "internal server error"}, ErrorClass.INVALID_RESPONSE_CONTRACT),
        (500, None, ErrorClass.INVALID_RESPONSE_CONTRACT),
        (500, {}, ErrorClass.INVALID_RESPONSE_CONTRACT),
        (502, {"error": "upstream_unavailable"}, ErrorClass.HTTP_502),
        (503, {"error": "upstream_unavailable"}, ErrorClass.HTTP_503),
        (504, None, ErrorClass.HTTP_504),
        (422, {"error": "cotacao_recusada", "motivo": "Idade acima do limite."}, ErrorClass.BUSINESS_REFUSAL),
        (422, {"error": "something_else"}, ErrorClass.VALIDATION_ERROR),
        (400, {"error": "payload_invalido"}, ErrorClass.INVALID_REQUEST),
        (401, None, ErrorClass.UNAUTHORIZED),
        (403, None, ErrorClass.FORBIDDEN),
        (404, None, ErrorClass.NOT_FOUND),
        (418, None, ErrorClass.INVALID_RESPONSE_CONTRACT),
    ],
)
def test_classify_response(status, body, expected):
    assert classify_response(status, body) == expected


@pytest.mark.parametrize(
    ("error_class", "expected"),
    [
        (ErrorClass.CONNECTION_ERROR, True),
        (ErrorClass.TIMEOUT, True),
        (ErrorClass.HTTP_500, True),  # the documented deviation
        (ErrorClass.HTTP_502, True),
        (ErrorClass.HTTP_503, True),
        (ErrorClass.HTTP_504, True),
        (ErrorClass.BUSINESS_REFUSAL, False),
        (ErrorClass.INVALID_REQUEST, False),
        (ErrorClass.VALIDATION_ERROR, False),
        (ErrorClass.UNAUTHORIZED, False),
        (ErrorClass.FORBIDDEN, False),
        (ErrorClass.NOT_FOUND, False),
        (ErrorClass.INVALID_RESPONSE_CONTRACT, False),
    ],
)
def test_is_retryable(error_class, expected):
    assert is_retryable(error_class) is expected


def test_http_500_is_retryable_only_for_the_known_transient_envelope():
    """Documented deviation: http_500 is retryable, but only when the body
    matches quote-service's own known transient envelope. An unrelated or
    malformed 500 body must not be silently retried."""
    assert is_retryable(classify_response(500, {"error": "upstream_unavailable"})) is True

    for malformed_body in (None, {}, {"error": "something_else"}, {"detail": "internal server error"}):
        error_class = classify_response(500, malformed_body)
        assert error_class == ErrorClass.INVALID_RESPONSE_CONTRACT
        assert is_retryable(error_class) is False


def test_next_backoff_seconds_is_exponential_and_capped():
    rng = random.Random(42)
    delay_1 = next_backoff_seconds(
        1, base_seconds=0.5, multiplier=2.0, max_seconds=4.0, jitter_fraction=0.0, rng=rng
    )
    delay_2 = next_backoff_seconds(
        2, base_seconds=0.5, multiplier=2.0, max_seconds=4.0, jitter_fraction=0.0, rng=rng
    )
    delay_10 = next_backoff_seconds(
        10, base_seconds=0.5, multiplier=2.0, max_seconds=4.0, jitter_fraction=0.0, rng=rng
    )
    assert delay_1 == pytest.approx(0.5)
    assert delay_2 == pytest.approx(1.0)
    assert delay_10 == pytest.approx(4.0)  # capped


def test_next_backoff_seconds_never_negative_even_with_high_jitter():
    rng = random.Random(1)
    for attempt in range(1, 5):
        delay = next_backoff_seconds(
            attempt, base_seconds=0.5, multiplier=2.0, max_seconds=4.0, jitter_fraction=0.9, rng=rng
        )
        assert delay >= 0.0
