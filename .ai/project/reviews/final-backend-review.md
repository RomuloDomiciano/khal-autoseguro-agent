# Final Backend Review

Executed against `.ai/workflows/review-backend.workflow.md`, as a genuine
independent pass following the code that was already implemented and
tested — not a restatement of the implementation report.

**Scope**: all of `agent-service/` as it stands at delivery time, plus its
interaction with the unmodified `quote-service` and the frontend's
integration against it.

**Task description / acceptance criteria** (from `CHALLENGE.md` and
`.ai/agents/backend-dev.yaml`): build an agent that converses with a lead,
qualifies them, requests a quote, and decides to resolve or hand off —
never fabricating a price, never crashing on quote-service instability,
with explicit retry policy, deterministic handoff, and full traceability.

## Step 1 — Review scope

Affected flows: qualification (LLM extraction + deterministic field
tracking), quotation (LLM tool-calling → typed client → real quote-service),
retry (bounded, classified), handoff (deterministic policy), and the API
surface consumed by the frontend. No interpretation of ambiguous intent was
required — the brief and `backend-dev.yaml` are explicit on all of these.

## Step 2 — Inspect the complete change

Full diff inspected: domain models, retry policy, handoff policy, LLM
abstraction, orchestrator, API layer, observability, `docker-compose.yml`,
both Dockerfiles, and the frontend integration layer (`api.ts`,
`useConversation.ts`). No changes found outside the requested scope.

One real defect was found and corrected during this pass (not merely
inspected and accepted): **`agent-service/Dockerfile` copied `pyproject.toml`
but not `uv.lock`**, so `uv sync --no-dev` inside the container would
re-resolve dependencies from `pyproject.toml`'s loose version ranges
instead of the exact pinned versions the test suite validated against —
a reproducibility gap, not merely a style issue, since a future rebuild
could silently pull different transitive dependencies than what was
tested. Fixed: `uv.lock` is now copied and `uv sync --no-dev --frozen` is
used, which fails the build outright if the lockfile and `pyproject.toml`
ever drift instead of silently re-resolving. Re-verified: `docker compose
build agent-service` succeeds and the container reaches `healthy`.

No other unintended changes, incomplete implementations, duplicated
behavior, or inconsistent patterns were found.

## Step 3 — Review by priority

**1. Quotation integrity.** Confirmed structural, not prompt-based: `get_quote`
arguments are rejected (`get_quote_args_match_profile`) if they don't
exactly match the confirmed `LeadProfile` before any external call is made;
on success, the lead-facing message and `QuoteSummary` are built by
`render_quote_message`/`to_quote_summary` directly from the typed
`QuoteResult` — the LLM has no code path to author that text. A regex
safety net (`_looks_like_a_price_mention`) additionally catches stray price
mentions in any other plain-text reply. All three layers have dedicated,
passing tests, including one that scripts a model directly trying to state
a price without calling the tool. No finding.

**2. Resilience.** Explicit connect (3s) / read (15s) timeouts; bounded 3
attempts; exponential backoff with jitter; explicit classification table
(`retry_policy.py`) distinguishing transient (`connection_error`,
`timeout`, `http_500/502/503/504`) from non-retryable (`422`, `400`, etc.).
The `http_500`-as-transient choice is a documented, narrow deviation from
the generic guidance in `backend-dev.yaml`, justified by direct inspection
of `quote-service/app/main.py` (500/502/503 share one simulated-instability
branch and error envelope). No silent exception swallowing found — the
top-level FastAPI exception handler logs full detail server-side and
returns a generic, safe response. No finding.

**3. Human handoff.** Nine reasons across two categories, each with a
templated (non-LLM) user-safe message. `HandoffRecord.summary` is now
exposed via the API (`GET /conversations/{id}`) — confirmed this closes a
real prior gap (the summary was computed and stored but not reachable by
any API consumer). Every handoff trigger is a countable, deterministic
condition; verified per-trigger tests exist for all nine. No finding.

**4. Security and sensitive-data exposure.** Raw lead message bodies are
never logged (verified: `message.received` logs only `conversation_id`,
`message_type`, `char_len`); `redact_pii` scrubs CPF/phone/email/plate
before anything else is logged or stored in a handoff summary; CEP is
truncated to its 2-digit prefix in logs. No stack traces reach the user
(verified via the exception handler). No hardcoded secrets found in a
repo-wide grep (`sk-proj`/`sk-ant`/generic key patterns — none present in
tracked or staged content). `.env` is correctly gitignored;
`.env.example` files contain placeholders only. No finding.

**5. Functional correctness vs. acceptance criteria.** Verified via the
full test suite (133 tests: 121 unit, 6 integration against the real
quote-service, 6 e2e against the real FastAPI app) and a live, unscripted
demo conversation against real OpenAI + real quote-service, which is
preserved in `agent-service/docs/`. No finding.

**6. Traceability.** `conversation_id`, `request_id` (via middleware,
`X-Request-Id`), `quote_request_id` (per logical attempt group, shared
across retries), `quote_id` (minted locally, explicitly distinguished from
an upstream id since quote-service issues none), `handoff_id` — all present
and exposed via `GET /conversations/{id}/quote-attempts`. No finding.

**7. Architecture and maintainability.** Layering is respected: routes are
thin (`app/api/routes/conversations.py` only maps DTOs and calls the
orchestrator); the quote-service and LLM provider are each isolated behind
a Protocol with one implementation; domain/policy modules have no HTTP or
LLM SDK import. One previously-dead field, `Conversation.pending_field`,
was confirmed unused (set once at construction, never reassigned, not
exposed via any schema — the orchestrator computes the real pending field
fresh every turn via `missing_required_fields()`) and has been removed;
`architecture.md` updated to describe the actual (correct) mechanism
instead of the removed field. No finding remaining.

**8. Test coverage.** Confirmed present for every priority area above,
including a previously-missing explicit test for the CEP-optional
contract and `data_inicio` pass-through (both were only incidentally
exercised before this pass, not asserted by name) — now covered by
`tests/unit/test_cep_and_start_date_contract.py`,
`tests/unit/test_tools.py`, and a new integration test proving pro-rata
comes back correctly from the real quote-service. No finding.

**9. Evidence-based performance risks.** None identified beyond the
already-documented, explicit limitation that in-memory storage and a
per-conversation `asyncio.Lock` are single-process only. Not a defect —
a scoped, stated limitation appropriate for this delivery.

## Step 4 — Verified findings

Only one confirmed, evidence-based finding was raised in this pass (the
Dockerfile lockfile gap), and it was corrected and re-verified within this
same review, per workflow guidance that a reviewer inspects the
implementation rather than merely trusting it. No other finding met the
bar of "affected behavior + evidence + concrete impact."

## Step 5 — Classification

**Ready** — see below.

## Step 6 — Review report

### Assessment

**Ready.** All priority areas were inspected against the actual code, the
one confirmed issue found during this pass (Dockerfile lockfile gap) was
corrected and re-verified, and the full test suite (133 backend + 26
frontend) passes. No blocking issue remains.

### Blocking issues

None found.

### Important issues

None found. (The Dockerfile lockfile gap was corrected within this same
review pass rather than left open, so it is not carried forward as an open
important issue — see Step 2/4 above for the evidence trail.)

### Suggestions

- `docker-compose.yml`'s `frontend` service has no healthcheck (unlike
  `quote-api`/`agent-service`) — not blocking, since nothing depends on its
  health, but a `wget`-based check could be added for symmetry if the
  `node:20-slim` image is later swapped for one that includes it.
- The `get_quote` argument-mismatch safety net is scoped to a single HTTP
  request's tool-calling loop, not the conversation's whole lifetime
  (documented as a known limitation) — worth closing if this ever becomes a
  concrete operational concern.
- A sanitized, offline dataset-evaluation fixture was found already present
  in the repository (`docs/dataset-analysis.md`,
  `tests/fixtures/offline_dataset_eval_cases.json`,
  `tests/unit/test_offline_dataset_eval_cases.py`) — not authored during
  this review, but inspected and confirmed passing, sanitized (no raw
  PII-shaped values), and not loaded by any production code path.

### Positive observations

- The anti-fabrication guarantee is structural (guard + deterministic
  template + regex net), not a single point of failure, and each layer has
  a dedicated test naming the exact scenario it defends against.
- The `http_500`-as-transient deviation is the kind of decision that's easy
  to get wrong by following generic guidance uncritically; it's justified
  here by reading the actual dependency's source, not assumption.
- The read-timeout-above-slow-duration decision was validated twice: once
  by a deterministic test, and once by an organic, unscripted occurrence
  during a live demo — stronger evidence than either alone.

### Validation gaps

- No gated live-LLM regression test exists in the automated suite (the
  live demo conversations were run manually). This is a known, documented
  gap, not something this review can close — release validation should
  treat it as an accepted limitation, not a blocking absence.
- Multi-worker / horizontal-scaling behavior was not validated at runtime
  (only reasoned about) — in-memory storage and process-local locking make
  this out of scope for the current delivery, not an oversight.

## Handoff

Assessment is **Ready** → proceed to `.ai/workflows/validate-backend.workflow.md`.
