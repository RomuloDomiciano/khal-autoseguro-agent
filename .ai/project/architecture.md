# AutoSeguro Architecture

## Status

Frontend: in progress, UI-only phase (see `context.md`).
Backend (`agent-service`): design complete, implementation starting.

This document must be updated as each side is implemented. It describes the
intended structure and must not contradict the actual code.

---

# Backend Architecture (`agent-service`)

## Architectural goals

- Never invent, estimate, or fabricate a quotation price; the quote-service
  response is the sole source of truth for price and eligibility.
- Treat quote-service as an unstable external dependency: explicit timeouts,
  bounded retries on transient failures only, no retry on business refusals.
- Make retry, failure-classification, and handoff decisions deterministic —
  never left to LLM judgment; the LLM extracts/converses, policy modules
  decide.
- Keep conversation state explicit and separate from transport concerns.
- Isolate the quote-service and the LLM provider each behind a typed
  client/adapter, so either can change without touching orchestration.
- Preserve traceability: `conversation_id`, `request_id`, `quote_request_id`,
  `quote_id`, `handoff_id` on every relevant record and log line.
- Protect personal data by default: redact PII from logs and handoff
  summaries; never send more than necessary to the LLM.

## Structure

```text
agent-service/
├── app/
│   ├── api/                  # FastAPI routers + request/response schemas (DTOs, camelCase)
│   │   ├── routes/
│   │   └── schemas.py
│   ├── agent/                 # orchestration: tool-calling loop, prompting, tool specs
│   │   ├── orchestrator.py
│   │   ├── prompting.py
│   │   ├── tools.py
│   │   └── policies/
│   │       └── handoff_policy.py
│   ├── domain/                 # typed domain models + pure policy logic, no I/O
│   │   ├── models.py           # Conversation, Message, LeadProfile, QuoteAttempt, HandoffRecord, enums
│   │   └── policies/
│   │       └── retry_policy.py # error classification, backoff math — independently unit-tested
│   ├── integrations/
│   │   ├── llm/                 # LLMClient Protocol, OpenAIChatClient, factory, FakeLLMClient (tests)
│   │   └── quote_service/       # QuoteServiceClient Protocol, httpx implementation
│   ├── observability/            # structlog config, redact_pii, correlation-id middleware
│   ├── config/                    # pydantic-settings, env var definitions
│   └── main.py
├── tests/
│   ├── fakes/                     # FakeLLMClient and other test doubles
│   └── ...                        # unit / integration / e2e, mirroring app/ structure
├── pyproject.toml
├── Dockerfile
└── .env.example
```

## Request flow

`Frontend → Agent Service API (app/api) → Conversation Orchestrator
(app/agent) → LLM with tool-calling (app/integrations/llm) → Quote Service
Client (app/integrations/quote_service) → Existing Quote Service`

The orchestrator is the only place these pieces meet; routers stay thin
(HTTP + DTO mapping only), and domain/policy modules have no HTTP or LLM
SDK dependency, so they're testable in isolation.

## Conversation state

`ConversationStatus`: `collecting → quoting → resolved | handed_off`
(`handed_off` is terminal; `resolved` allows further plain-text replies
without re-entering the quote flow). The orchestrator derives the currently
pending qualification field on every turn from `LeadProfile.missing_required_fields()`
— fixed order `veiculo_ano → idade → cep → plano_id` — rather than storing it
as separate conversation state, so there's a single source of truth for
"what's missing" instead of two that could drift. A deterministic
2-attempts-per-field cap applies before handoff. This mirrors the intent of
the frontend's original mock state machine (`mockAgent.ts`, now kept only as
an offline demo, not wired to production) so the two stay conceptually
compatible.

## LLM integration

One `LLMClient` Protocol (`complete(messages, tools, ...) -> LLMToolResult`),
one `OpenAIChatClient` implementation, one factory keyed off
`LLM_PROVIDER`/`LLM_MODEL`/`OPENAI_API_KEY`. Conversation state, field
validation, quote-request construction, quote-service integration,
timeout/retry policy, handoff policy, and observability all stay
independent of which provider is behind `LLMClient` — adding a second
provider later means one new file, not a rewrite.

Two tools are exposed to the model: `record_lead_info` (structured
extraction only, touches nothing external) and `get_quote` (the
orchestrator validates the args against the already-confirmed
`LeadProfile` before executing, then calls the real quote-service). The
`kind: "quote"` message and its price/coverage summary sent to the lead are
always built by a deterministic server-side template from the typed
`QuoteResult`, never from LLM-generated text — this is a structural
guarantee against fabricated prices, not just a prompting rule.

## Resilience

Quote-service calls: explicit connect/read timeouts, max 3 attempts with
exponential backoff + jitter, retryable only for `connection_error`,
`timeout`, and `http_500/502/503/504` (this project's quote-service emits
500/502/503 from the same simulated-instability branch with an identical
`upstream_unavailable` envelope, so 500 is treated as transient here — a
deliberate, documented deviation from the generic 502/503/504-only list).
Business refusals (`422 cotacao_recusada`) and malformed-request errors
(`400 payload_invalido`) are never retried. Read timeout is set comfortably
above the quote-service's simulated slow-response duration, so a
slow-but-successful call isn't misclassified as a failure.

---

# Frontend Architecture

## Architectural goals

The frontend architecture should:

- remain simple and easy to explain
- separate visual components from the conversation/agent logic
- make loading and failure states explicit
- support automated testing
- avoid unnecessary abstractions
- keep the real backend integration and the offline demo mock impossible to
  confuse with each other

## Structure

```text
src/
├── app/
│   └── App.tsx           # root composition
├── features/
│   └── chat/
│       ├── ChatPage.tsx          # page layout
│       ├── ChatWindow.tsx        # message list + input, orchestration
│       ├── MessageBubble.tsx     # renders one message (text/quote/handoff)
│       ├── QuoteCard.tsx         # renders a quote result
│       ├── MessageInput.tsx      # text input + send
│       ├── TypingIndicator.tsx
│       ├── api.ts                # real agent-service HTTP client (fetch + DTO mapping)
│       ├── useConversation.ts    # real conversation hook — production data source
│       └── types.ts              # Message, Quote, conversation types
├── demo/
│   ├── README.md                    # explicitly labeled non-production
│   ├── offlineMockAgent.ts          # scripted, backend-free pricing/state machine
│   └── useOfflineMockConversation.ts # drives the offline demo, not wired to any route
├── test/
│   └── setup.ts           # Vitest + Testing Library setup
├── index.css               # design tokens + base styles
└── main.tsx
```

## Conventions

- Production conversation logic (`features/chat/useConversation.ts` +
  `api.ts`) is the single seam that talks to `agent-service`. Presentational
  components must not call it directly for anything beyond the hook's
  returned state and actions.
- `src/demo/` is a separate, clearly-labeled tree for the offline,
  backend-free UI demo. Nothing under `features/` may import from `demo/`,
  and nothing under `demo/` is wired into `App.tsx`'s render path — it
  exists only to be run standalone if someone wants a backend-free demo.
- One CSS file per component/feature, co-located, using the CSS custom
  properties defined in `src/index.css`.
- No global state library; conversation state lives in the chat feature's
  hook. Reassess only if a second feature needs to share state.
