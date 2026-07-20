# Final Backend Validation Report

Executed against `.ai/workflows/validate-backend.workflow.md`. Input: this
delivery's implementation plus `final-backend-review.md` (assessment:
**Ready**, one issue found and corrected within that same review pass — the
Dockerfile lockfile gap — no blocking or open important issue remained
afterward).

## Step 1 — Delivery scope

Included: `agent-service/` (full backend), `docker-compose.yml`
(full-stack orchestration), `frontend/` integration against the real API
(`useConversation.ts`/`api.ts`), `.ai/` consistency fixes, root `README.md`.
Config/env changes: new `CORS_ALLOW_ORIGINS` setting; `agent-service`
Dockerfile now copies and freezes against `uv.lock`. Dependency changes:
none added: this pass only fixed how existing dependencies are resolved in
the container build. Documented known limitations: see below. No unresolved
review suggestions carry a blocking weight (all three are explicitly
non-blocking per the review report).

## Step 2 — Repository hygiene

Checked: no temporary logs, no dead/commented-out code, no hardcoded
secrets or environment-specific URLs (`docker-compose.yml`'s internal URL
`http://quote-api:8000` is a compose service name, not environment-specific
in the sense that matters — it only resolves inside the compose network).
No placeholder/fabricated values in the quotation path. No exposed
sensitive fields in logs (verified live, see Step 6). `.env.example` files
are complete and placeholder-only. No TODOs left in required behavior. No
unrelated modifications found. No accidental files (`git add -n .`
inspected; only expected paths, no `node_modules`/`.venv`/`dist`/`.env`).

## Step 3 — Automated validation

| Command | Result |
|---|---|
| `cd agent-service && uv run pytest` | **133 passed** (121 unit, 6 integration against a real quote-service subprocess, 6 e2e), 1 unrelated deprecation warning (`httpx`/`TestClient`), 0 failures |
| `cd frontend && npm run lint` | **passed**, 0 errors |
| `cd frontend && npm run typecheck` | **passed**, 0 errors |
| `cd frontend && npm run test -- --run` | **26 passed** (5 files) |
| `cd frontend && npm run build` | **passed**, produced `dist/` |
| `docker compose config` | **passed** — valid, resolves correctly (output redacted before display; the real `OPENAI_API_KEY` was briefly echoed by this command on a first, uncredacted run earlier in this session — noted transparently under Step 8, not concealed) |
| `docker compose up --build -d` | **passed** — all three containers started |
| `docker compose build agent-service` (after the Dockerfile fix) | **passed** |

No command was skipped; none reported as passing without having actually
been run.

## Step 4 — Functional behavior (runtime-validated)

Verified live against the running Docker stack (not only via pytest):

- **Qualification flow**: a single message providing vehicle/age/CEP/plan
  was correctly extracted and resolved to a quote in one turn.
- **Successful quotation path**: response came only from `quote-service`
  — confirmed via live logs showing `POST http://quote-api:8000/quote →
  200`, followed by `quote.outcome` with `final_status: succeeded`.
- **Transient handling / no fabrication under slowness**: this specific
  live run's single attempt took **8048ms** (the quote-service's simulated
  slow-response branch) and still returned a valid, correct quote — not
  misclassified as a failure, exactly the scenario named in the challenge
  brief. This happened organically, unscripted, during this validation
  pass.
- **Retry exhaustion / non-retryable handling**: validated via
  `tests/integration/test_quote_service_client.py`, which forces
  `QUOTE_FAILURE_RATE=1.0` (exhausts all 3 retries against the real
  service, asserts no price anywhere in the result) and forces a
  deterministic `422` business refusal (asserts exactly 1 attempt, never
  retried). These are real HTTP calls against a real quote-service
  subprocess, not mocked.
- **Human handoff**: `tests/unit/test_orchestrator.py` and
  `tests/e2e/test_api.py` cover all nine handoff reasons; each asserts a
  machine-readable reason and a non-empty, price-free user message.
- **`conversation_id` and correlation identifiers in logs**: confirmed live
  (see the log excerpt in Step 6) — `conversation_id`, `request_id`,
  `quote_request_id`, and `quote_id` all present and correlated across the
  same request.
- **Quotation status recorded per attempt**: confirmed live
  (`quote.attempt.start` → `quote.attempt.result` → `quote.outcome`).
- **No price fabricated on any tested failure path**: confirmed by the
  price-guard test matrix (`tests/unit/test_price_guard.py`) and the
  structural guarantee inspected in the review.

## Step 5 — Resilience

- Explicit timeouts confirmed (`QUOTE_SERVICE_CONNECT_TIMEOUT_SECONDS=3.0`,
  `QUOTE_SERVICE_READ_TIMEOUT_SECONDS=15.0` in `.env.example` and
  `Settings`).
- Retries bounded at 3 (`QUOTE_SERVICE_MAX_ATTEMPTS`), never infinite.
- Only `connection_error`, `timeout`, `http_500/502/503/504` retried
  (`retry_policy._RETRYABLE`); `400/401/403/404/422` never retried —
  confirmed by `tests/unit/test_retry_policy.py`'s full parametrized table.
- Backoff applied between attempts (exponential + jitter,
  `next_backoff_seconds`).
- Retry exhaustion produces a handoff
  (`quote_service_unavailable_after_retries`), never a fabricated price.
- Duplicate-request control: `POST /quote` is a pure computation with no
  side effects in the provided service, so retrying it is inherently safe;
  a per-conversation `asyncio.Lock` prevents concurrent double-processing
  of the same conversation within one process (documented single-process
  limitation).

## Step 6 — Observability

Confirmed traceable, live (excerpt from the running container, secrets
redacted, full lines otherwise unmodified):

```
{"conversation_id": "conv_6fee93451bf5", "event": "conversation.created", "request_id": "req_cadca2bbcb5a", ...}
{"conversation_id": "conv_6fee93451bf5", "message_type": "text", "char_len": 52, "event": "message.received", "request_id": "req_134824431fba", ...}
{"conversation_id": "conv_6fee93451bf5", "quote_request_id": "qreq_537b1fb0ea54", "attempt_number": 1, "plano_id": "completo", "idade": 35, "veiculo_ano": 2018, "cep_prefix": "01", "event": "quote.attempt.start", ...}
{"conversation_id": "conv_6fee93451bf5", "quote_request_id": "qreq_537b1fb0ea54", "attempt_number": 1, "http_status": 200, "error_class": null, "status": "succeeded", "latency_ms": 8048, "event": "quote.attempt.result", ...}
{"conversation_id": "conv_6fee93451bf5", "quote_id": "qte_0e82d19a", "quote_request_id": "qreq_537b1fb0ea54", "final_status": "succeeded", "total_attempts": 1, "event": "quote.outcome", ...}
```

Note the log line for `message.received` carries only `char_len`, never
the message body itself — the lead's actual words ("Corolla 2018, 35 anos,
CEP 01310-100, plano completo") never appear anywhere in these logs. `cep`
appears only as its 2-digit prefix (`"01"`), never the full value.
`request_id`, `quote_request_id`, and `quote_id` are all present and
correctly correlated across every line of the same request. No CPF,
phone, e-mail, or address ever appears — none was volunteered in this run,
and `tests/e2e/test_pii_logging.py` separately proves that when one is
volunteered, it still doesn't appear in logs.

## Step 7 — Handoff behavior

Confirmed by code inspection and test coverage (`test_handoff_policy.py`,
`test_orchestrator.py`, `test_api.py`): every handoff has a machine-readable
reason from a fixed enum, a non-empty user-safe message, a preserved
(and now API-exposed) summary, never a fabricated quotation, and a clear
technical/business category split.

## Step 8 — Security and privacy

- No exposed secrets or tokens in tracked/staged files (`git grep` for key
  patterns: empty).
- No sensitive data in structured logs (Step 6).
- No stack traces or internal error details returned to users (top-level
  exception handler returns a fixed, generic message; verified by reading
  `app/observability/errors.py`).
- No unnecessary personal data sent to the LLM (only qualification fields
  and conversation text — never CPF/phone/email, which aren't collected at
  all).
- In-memory persistence only — no unsafe on-disk persistence of
  conversation data.
- Environment variables fully documented in both `.env.example` files.
- **Self-reported incident**: during this same validation pass, an
  unredacted `docker compose config` invocation briefly displayed the real
  `OPENAI_API_KEY` in this session's own tool output before a redaction
  filter was applied to all subsequent invocations. This is not a
  repository/commit exposure — the key was never written to any tracked or
  staged file, and `git grep` across tracked/staged content confirms this.
  It is disclosed here rather than omitted, per this workflow's integrity
  rules. Recommended action for the user: treat the key as exposed in this
  session's transcript and rotate it if that matters for their threat
  model; this does not block delivery since no repository artifact is
  affected.

## Step 9 — Reconcile review report

All items from `final-backend-review.md` are resolved: the one confirmed
finding (Dockerfile lockfile gap) was fixed and re-verified within the
review pass itself; all three suggestions are explicitly non-blocking and
carried forward as documented, accepted trade-offs, not silently dropped.
No implementation change occurred after the review that would require
re-review.

## Step 10 — Release decision

**Ready with known limitations.**

Mandatory behavior is valid, both categories of automated checks pass, the
primary quotation flow is verified end-to-end (including live, in
production-shaped Docker containers), no price fabrication path exists on
any tested failure mode, and no blocking security/data-protection issue
was found. The limitations below are confirmed, documented, don't
compromise quotation integrity, security, or mandatory handoff behavior,
and don't violate any acceptance criterion — they're scope boundaries
appropriate to a 3-day take-home, not defects.

## Step 11 — Validation report summary

### Release decision

**Ready with known limitations** (see Step 10 for justification).

### Automated evidence

See Step 3's table — every command's exact result is recorded there.

### Manual and runtime evidence

See Step 4 and the live log excerpt in Step 6 — obtained by driving the
actual running Docker Compose stack, not only by inspecting code or running
pytest.

### Code-inspection evidence

See `final-backend-review.md`'s per-priority findings (quotation
integrity, resilience, handoff, security, architecture).

### Unavailable evidence

- No real browser walkthrough of the frontend was performed in this
  session (no browser-automation tool available here) — the frontend's
  integration against the real API was verified at the HTTP-contract level
  (live curl calls with the frontend's own `Origin` header, real CORS
  headers returned, real quote resolved) but not by observing the rendered
  UI. This is an explicit gap for the user to close, not something this
  validation can claim.
- No gated live-LLM contract test exists in CI; the live-LLM evidence in
  this report and in `agent-service/docs/` is from manual runs, not an
  automated, repeatable check.

### Known limitations

- In-memory conversation storage only (no persistence across restarts, not
  safe across multiple worker processes) — documented, doesn't affect
  quotation integrity or handoff correctness for a single-process
  deployment.
- No authentication or rate-limiting on the API — explicitly out of scope
  per the challenge brief.
- `get_quote` argument-mismatch protection is scoped to a single HTTP
  request's tool-calling loop, not the conversation's full lifetime.
- Dataset-based evaluation exists as a small, sanitized, offline fixture
  (`docs/dataset-analysis.md`, `agent-service/tests/fixtures/offline_dataset_eval_cases.json`,
  checked by `test_offline_dataset_eval_cases.py`) — found already present
  in the repository during this validation pass (not authored as part of
  this review/validate cycle), verified to pass against current code, and
  confirmed to load nothing at runtime.
- No gated live-LLM regression test in the automated suite.
- Frontend UI never visually verified in a real browser during this
  delivery pass.

## Handoff

**Ready with known limitations** → this backend change may proceed to
submission/demonstration with the limitations above included in delivery
notes (now reflected in the root `README.md`'s own Limitations section).
