# AutoSeguro Agent Service

Backend for the AutoSeguro WhatsApp lead-qualification agent: converses with a
lead → qualifies them → requests a quote from `quote-service` → resolves the
conversation or hands off to a human, with explicit, traceable state at every
step. Built for the Namastex FDE take-home challenge (see `../CHALLENGE.md`).

The backend was built and validated independently of the frontend first;
`../frontend` is now consolidated into this repo and wired to call this API
for real (`frontend/src/features/chat/useConversation.ts` + `api.ts`). Its
original offline mock (`frontend/src/demo/`) is kept only as a
backend-free UI demo — it is not used by the production chat flow.

## Running it

Requires [uv](https://docs.astral.sh/uv/) and the `quote-service` running
(see `../quote-service/README.md` or `../docker-compose.yml` — it's expected
at `http://localhost:8000` by default).

```bash
cd agent-service
cp .env.example .env
# edit .env: set OPENAI_API_KEY

uv sync
uv run uvicorn app.main:app --reload --port 8080
```

Health check: `curl http://localhost:8080/health`

### Tests

```bash
uv run pytest              # unit + integration (spins up quote-service itself) + e2e
uv run pytest tests/unit    # no external dependencies, no quote-service needed
```

The integration and e2e suites start `quote-service` themselves as a
subprocess, controlling its `QUOTE_FAILURE_RATE` / `QUOTE_SLOW_RATE` /
`QUOTE_SEED` env vars per test — so failure, slowness, and refusal paths are
exercised deterministically against the *real* dependency, not a mock of it.
No `OPENAI_API_KEY` is required to run the suite: an `LLMClient` Protocol
with a scriptable `FakeLLMClient` test double keeps orchestration logic
testable without any network call or cost.

### Demo conversation

`docs/conversation-log.md` is one complete, real conversation (real OpenAI
LLM, real `quote-service`) from greeting to a resolved quote — the
deliverable required by the challenge. `docs/conversation-log-resilience-example.md`
is a second real run, kept because it happened to hit an organic transient
failure and an organic slow-but-successful call, which is exactly the
scenario this project weights most heavily; nothing in it was forced or
scripted.

## API

Base path `/api/v1`.

| Method & path | Purpose |
|---|---|
| `POST /conversations` | Start a conversation, returns the greeting message. |
| `POST /conversations/{id}/messages` | Send a lead message; returns the messages produced this turn and the resulting conversation status. |
| `GET /conversations/{id}` | Full state: profile, all messages, all quote attempts, handoff (if any). |
| `GET /conversations/{id}/quote-attempts` | Just the quote-attempt trace — one entry per HTTP try against `quote-service`, with status/error class/latency. |
| `GET /health` | Liveness of this service only — deliberately does **not** proxy `quote-service`'s health, since the point of the challenge is that this service must stay up regardless of the downstream's state. |

`ConversationStatus`: `collecting → quoting → resolved | handed_off` (the
last is terminal). Response bodies are camelCase to match the frontend's
TypeScript types (`app/api/schemas.py` is the only place that mapping
happens; internal domain models stay snake_case).

## Decisions, and why

**LLM-driven, but conversation state is not LLM memory.** The model
(OpenAI, via a provider-agnostic `LLMClient` Protocol — see below) drives
natural-language understanding and extraction, but `LeadProfile`,
`ConversationStatus`, retry counts, and handoff triggers are all explicit
application state tracked by the orchestrator. Re-asking a question, giving
up on a field, retrying a quote, and deciding to hand off are all
deterministic decisions made in Python, never left to the model's judgment.
This is what makes the failure-handling story testable and defensible
rather than "hopefully the prompt handles it."

**The price the lead sees is never LLM-generated text.** The model can
*request* a quote via the `get_quote` tool, but the orchestrator (a)
rejects the call outright if its arguments don't exactly match the
already-confirmed `LeadProfile` — guarding against the model inventing or
silently changing a value on the one tool call that reaches an external
system — and (b) on success, builds the lead-facing message and
`QuoteSummary` with a deterministic template (`app/agent/rendering.py`)
directly from the typed `QuoteResult` the quote-service returned. The model
never authors that text. On any failure, the tool result fed back to the
model contains no numeric fields at all, and a regex safety net (matching
`R$`, `BRL`, `reais`, `/mês`, `por mês`, and `mensalidade de` patterns —
see `app/agent/orchestrator.py`'s `_looks_like_a_price_mention`) scans any
plain-text reply generated outside a successful quote and replaces it with
a canned fallback if it ever mentions a price. It's deliberately narrow
enough to never flag ordinary numbers like vehicle years, ages, CEPs, or
trace ids (`tests/unit/test_price_guard.py` proves both sides) —
belt-and-suspenders on top of a guarantee that shouldn't need it.

**`http_500` is treated as a retryable, transient failure here — a
deliberate, narrow deviation.** The generic guidance this project started
from lists only 502/503/504 as transient. Direct inspection of
`quote-service/app/main.py` shows this specific service emits 500/502/503
from the *identical* simulated-instability branch, with the same
`upstream_unavailable` envelope — for this dependency, 500 is not a
distinct failure mode, it's the same coin flip as 502/503. Treating it as
non-retryable would silently drop retry coverage for roughly a third of all
simulated infra failures, directly undermining the challenge's most heavily
weighted criterion ("what does the agent do when `/quote` fails"). This is
scoped to responses matching this service's known envelope, not a blanket
"always retry 500" rule: a 500 with an unrelated or malformed body is
classified as `invalid_response_contract` instead and is terminal, never
retried — see `app/domain/policies/retry_policy.py` for the full
classification table and reasoning,
`tests/unit/test_retry_policy.py::test_http_500_is_retryable_only_for_the_known_transient_envelope`
for the classifier-level proof of both sides, and
`tests/integration/test_quote_service_client.py` for both a test that
forces the retryable path against the real service and a mocked test
proving the malformed-body path is never retried.

**The read timeout (15s) is set deliberately above the quote-service's
simulated slow-response duration (8s default).** A naive short timeout
would misclassify a slow-but-successful call as a failure — exactly the
trap the challenge brief calls out by name. This is proven against the
real service, not asserted in the abstract: see
`test_slow_but_successful_call_is_not_misclassified_as_a_failure`, and the
organic example in `docs/conversation-log-resilience-example.md` where this
happened for real, unscripted, during the demo run.

**Retry policy is bounded and classification is explicit, never a blanket
try/except.** Max 3 attempts, exponential backoff with jitter. `422
cotacao_recusada` (a legitimate business refusal — age or vehicle outside
accepted ranges, unknown plan) and `400 payload_invalido` (would mean *our*
request was malformed) are never retried; both are terminal and route to a
handoff with a distinct, correct reason. `quote-service` itself is treated
as the sole source of truth for eligibility and price — this service never
re-implements or duplicates its business rules locally (`GET /planos` is
only used to describe plan names/coverages to the lead in conversation).

**Handoff reasons are a fixed, machine-readable set** (see
`app/domain/models.py`'s `HandoffReasonTechnical` / `HandoffReasonBusiness`
and `app/agent/policies/handoff_policy.py`), each with a templated —
never LLM-generated — user-facing message and a redacted conversation
summary. Every handoff is triggered by a countable, deterministic
condition (attempt counts, HTTP status, tool-loop iteration bound,
consecutive LLM-call failures) rather than an LLM self-reported confidence
score, which itself would be a judgment call this project deliberately
avoids delegating to the model. The summary is exposed via
`GET /conversations/{id}` (`handoff.summary`) so a human operator picking
up the conversation has enough context — collected profile fields and the
machine-readable reason — to continue without re-asking the lead
everything from scratch; it's built from redacted data only (see PII
handling below), never raw.

**Two tools, no MCP.** `record_lead_info` (pure extraction, touches
nothing external) and `get_quote` (the only tool that reaches
`quote-service`, and only after the arg-match guard above). A full MCP
server for a single internal tool would be infrastructure this challenge
doesn't need; the `LLMClient` Protocol already isolates the LLM provider
without it.

**LLM provider is swappable in principle, minimal in practice.** One
`LLMClient` Protocol (`app/integrations/llm/base.py`), one
`OpenAIChatClient` implementation, one factory keyed off
`LLM_PROVIDER`/`LLM_MODEL`/`OPENAI_API_KEY`. Adding Anthropic later means a
new file implementing the same Protocol and one new branch in
`factory.py` — no change to orchestration, retry policy, handoff policy,
or observability, which are all provider-independent by construction.

**PII is redacted by default, and mostly just never logged.**
`app/observability/redact.py` scrubs CPF/phone/email/plate patterns from
anything that does get logged or put in a handoff summary (`redact_pii`),
and truncates CEP to its 2-digit region prefix (`redact_cep`) everywhere a
CEP is exposed for observability or handed to a human operator — logs and
`handoff_policy.render_summary()` alike. The full CEP is never removed
from operational state (`LeadProfile`, the quote request itself) — only
the human-facing summary and log lines are redacted, since quoting
legitimately needs the real value. But the stronger guarantee is
architectural: the raw lead message body is never logged at all
(`message.received` logs only `conversation_id`, `message_type`, and
`char_len`) — there's nothing to redact because it was never written down
in the first place. `tests/e2e/test_pii_logging.py` captures real log
output and asserts a volunteered CPF/phone never appears in it;
`tests/unit/test_handoff_policy.py` asserts the full CEP never appears in
a rendered handoff summary, and that the operational
`lead_profile_snapshot` still carries it in full.

**In-memory conversation storage — an explicit, scoped limitation, not an
oversight.** `ConversationRepository` (`app/domain/repository.py`) is a
Protocol; `InMemoryConversationRepository` is the only implementation.
State is lost on restart and isn't safe across multiple worker processes.
Swapping in Redis/Postgres later means implementing the Protocol — nothing
in the orchestrator, API layer, or policies changes.

## Known limitations

- **In-memory storage only** (see above) — acceptable for this challenge,
  not for production.
- **CEP is soft-required, by contract, not by oversight**: `quote-service`
  itself treats a missing CEP as fully valid input (region multiplier
  defaults to 1.0, not a refusal — see `quote_logic.py`), so the agent has
  no correctness reason to be stricter than the system it's quoting
  against. The prompt asks for it once; there's no attempt-counter for it
  the way there is for the three hard-required fields, because there's
  nothing to enforce — proceeding without it is a fully valid outcome, not
  a degraded one. Proven by
  `tests/unit/test_cep_and_start_date_contract.py`. This is a deliberate
  divergence from the frontend's original offline demo (`frontend/src/demo/`),
  which hard-blocks on missing CEP; worth reconciling if that demo is ever
  promoted to production.
- **`data_inicio` is not an LLM-settable input.** It drives
  `quote-service`'s pro-rata first-payment math, and unlike the four
  qualification fields there is no extraction step or `LeadProfile` field
  to hold a confirmed value for it, so `get_quote`'s tool spec has no
  `data_inicio` parameter — the agent never asks for a start date and
  never lets the model supply one. Even a non-conformant tool call that
  includes `data_inicio` anyway is silently dropped by
  `parse_get_quote_args` before it reaches `quote-service`. Proven by
  `tests/unit/test_cep_and_start_date_contract.py::test_llm_supplied_data_inicio_never_reaches_the_quote_request`.
  The `QuoteRequestPayload`/`data_inicio` wire field still exists (it
  mirrors `quote-service`'s contract 1:1) and is exercised directly,
  bypassing the LLM, by
  `tests/integration/test_quote_service_client.py::test_data_inicio_not_on_the_first_of_the_month_returns_pro_rata_from_quote_service`.
- **No authentication or rate-limiting** on the API — out of scope per the
  challenge brief; would be required before any real deployment.
- **Single quote-service base URL, no service discovery** — fine for a
  local/demo deployment, not for a distributed one.
- **The `get_quote` argument-mismatch guard trips on a second consecutive
  mismatch within the same tool-calling turn** (bounded by
  `MAX_TOOL_ITERATIONS`), not across separate inbound messages — scoped
  this way because the tool-calling loop only spans a single HTTP request;
  see `app/agent/orchestrator.py`.
