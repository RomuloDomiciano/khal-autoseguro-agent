from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config.settings import Settings
from app.domain.models import ErrorClass, QuoteAttempt, QuoteAttemptStatus, QuoteRequestPayload, QuoteResult
from app.domain.policies import retry_policy
from app.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QuoteServiceOutcome:
    attempts: list[QuoteAttempt] = field(default_factory=list)
    final_status: QuoteAttemptStatus = QuoteAttemptStatus.PENDING
    result: QuoteResult | None = None
    refusal_reason: str | None = None


class QuoteServiceClient(Protocol):
    async def get_plans(self) -> dict: ...

    async def health(self) -> bool: ...

    async def request_quote(
        self,
        payload: QuoteRequestPayload,
        *,
        conversation_id: str,
        quote_request_id: str,
    ) -> QuoteServiceOutcome: ...


class HttpxQuoteServiceClient:
    """Isolates quote-service behind a typed client. Applies explicit
    timeouts and the bounded-retry policy from retry_policy.py; the classify
    / document deviation logic itself lives there, not here — this class
    just executes it and records a QuoteAttempt per HTTP try."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = httpx.Timeout(
            connect=settings.quote_service_connect_timeout_seconds,
            read=settings.quote_service_read_timeout_seconds,
            write=settings.quote_service_connect_timeout_seconds,
            pool=settings.quote_service_connect_timeout_seconds,
        )

    async def get_plans(self) -> dict:
        async with httpx.AsyncClient(base_url=self._settings.quote_service_base_url, timeout=self._timeout) as client:
            response = await client.get("/planos")
            response.raise_for_status()
            return response.json()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.quote_service_base_url, timeout=self._timeout
            ) as client:
                response = await client.get("/health")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def request_quote(
        self,
        payload: QuoteRequestPayload,
        *,
        conversation_id: str,
        quote_request_id: str,
    ) -> QuoteServiceOutcome:
        outcome = QuoteServiceOutcome()
        max_attempts = self._settings.quote_service_max_attempts

        async with httpx.AsyncClient(base_url=self._settings.quote_service_base_url, timeout=self._timeout) as client:
            for attempt_number in range(1, max_attempts + 1):
                attempt = await self._try_once(
                    client,
                    payload,
                    conversation_id=conversation_id,
                    quote_request_id=quote_request_id,
                    attempt_number=attempt_number,
                )
                outcome.attempts.append(attempt)

                if attempt.status == QuoteAttemptStatus.SUCCEEDED:
                    outcome.final_status = QuoteAttemptStatus.SUCCEEDED
                    outcome.result = attempt.result
                    return outcome

                if attempt.status == QuoteAttemptStatus.REFUSED:
                    outcome.final_status = QuoteAttemptStatus.REFUSED
                    outcome.refusal_reason = attempt.error_detail
                    return outcome

                if attempt.status == QuoteAttemptStatus.REJECTED_INVALID:
                    outcome.final_status = QuoteAttemptStatus.REJECTED_INVALID
                    return outcome

                if attempt.status == QuoteAttemptStatus.INVALID_RESPONSE:
                    outcome.final_status = QuoteAttemptStatus.INVALID_RESPONSE
                    return outcome

                # Transient failure — retry if attempts remain.
                if attempt_number < max_attempts:
                    delay = retry_policy.next_backoff_seconds(
                        attempt_number,
                        base_seconds=self._settings.quote_service_backoff_base_seconds,
                        multiplier=self._settings.quote_service_backoff_multiplier,
                        max_seconds=self._settings.quote_service_backoff_max_seconds,
                        jitter_fraction=self._settings.quote_service_backoff_jitter,
                    )
                    logger.info(
                        "quote.attempt.retry_scheduled",
                        conversation_id=conversation_id,
                        quote_request_id=quote_request_id,
                        attempt_number=attempt_number,
                        next_attempt_in_ms=int(delay * 1000),
                    )
                    await asyncio.sleep(delay)

        # Every attempt still in outcome.attempts at this point returned
        # early from the loop as RETRYING (the terminal statuses above all
        # return before reaching here) — the last one exhausted the retry
        # budget rather than being retried, so its own status must say so.
        outcome.final_status = QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
        if outcome.attempts:
            outcome.attempts[-1].status = QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED
        return outcome

    async def _try_once(
        self,
        client: httpx.AsyncClient,
        payload: QuoteRequestPayload,
        *,
        conversation_id: str,
        quote_request_id: str,
        attempt_number: int,
    ) -> QuoteAttempt:
        started = time.monotonic()
        logger.info(
            "quote.attempt.start",
            conversation_id=conversation_id,
            quote_request_id=quote_request_id,
            attempt_number=attempt_number,
            plano_id=payload.plano_id.value,
            idade=payload.idade,
            veiculo_ano=payload.veiculo_ano,
            cep_prefix=(payload.cep or "")[:2] or None,
        )

        try:
            response = await client.post(
                "/quote",
                json=payload.model_dump(mode="json"),
                headers={"X-Request-Id": quote_request_id},
            )
        except Exception as exc:  # noqa: BLE001 — classified explicitly below
            error_class = retry_policy.classify_transport_exception(exc)
            attempt = QuoteAttempt(
                conversation_id=conversation_id,
                quote_request_id=quote_request_id,
                attempt_number=attempt_number,
                status=QuoteAttemptStatus.RETRYING
                if retry_policy.is_retryable(error_class)
                else QuoteAttemptStatus.FAILED_TRANSIENT_EXHAUSTED,
                request_payload=payload,
                error_class=error_class,
                error_detail=str(exc),
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            self._log_result(conversation_id, quote_request_id, attempt)
            return attempt

        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code == 200:
            try:
                result = QuoteResult.model_validate(response.json())
            except Exception as exc:  # noqa: BLE001 — invalid contract, not a crash
                attempt = QuoteAttempt(
                    conversation_id=conversation_id,
                    quote_request_id=quote_request_id,
                    attempt_number=attempt_number,
                    status=QuoteAttemptStatus.INVALID_RESPONSE,
                    request_payload=payload,
                    http_status=response.status_code,
                    error_class=ErrorClass.INVALID_RESPONSE_CONTRACT,
                    error_detail=str(exc),
                    latency_ms=latency_ms,
                )
                self._log_result(conversation_id, quote_request_id, attempt)
                return attempt

            attempt = QuoteAttempt(
                conversation_id=conversation_id,
                quote_request_id=quote_request_id,
                attempt_number=attempt_number,
                status=QuoteAttemptStatus.SUCCEEDED,
                request_payload=payload,
                http_status=response.status_code,
                result=result,
                latency_ms=latency_ms,
            )
            self._log_result(conversation_id, quote_request_id, attempt)
            return attempt

        body: dict | None
        try:
            body = response.json()
        except ValueError:
            body = None

        error_class = retry_policy.classify_response(response.status_code, body)

        if error_class == ErrorClass.BUSINESS_REFUSAL:
            status = QuoteAttemptStatus.REFUSED
        elif not retry_policy.is_retryable(error_class):
            status = QuoteAttemptStatus.REJECTED_INVALID
        else:
            status = QuoteAttemptStatus.RETRYING

        attempt = QuoteAttempt(
            conversation_id=conversation_id,
            quote_request_id=quote_request_id,
            attempt_number=attempt_number,
            status=status,
            request_payload=payload,
            http_status=response.status_code,
            error_class=error_class,
            error_detail=(body or {}).get("motivo") or (body or {}).get("message") or (body or {}).get("detalhe"),
            latency_ms=latency_ms,
        )
        self._log_result(conversation_id, quote_request_id, attempt)
        return attempt

    @staticmethod
    def _log_result(conversation_id: str, quote_request_id: str, attempt: QuoteAttempt) -> None:
        logger.info(
            "quote.attempt.result",
            conversation_id=conversation_id,
            quote_request_id=quote_request_id,
            attempt_number=attempt.attempt_number,
            http_status=attempt.http_status,
            error_class=attempt.error_class.value if attempt.error_class else None,
            status=attempt.status.value,
            latency_ms=attempt.latency_ms,
        )
