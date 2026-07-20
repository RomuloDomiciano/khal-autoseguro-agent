# Project Context

## Project

This context covers the **AutoSeguro** take-home challenge (Namastex FDE /
AI Engineer). AutoSeguro is a fictional car insurer whose sales team
qualifies leads and quotes policies over WhatsApp. The challenge brief is
`CHALLENGE.md` at the repo root — treat it as the source of truth for
requirements; this file only records project-specific decisions.

Consolidated into a single repo (`namastex-fde-challenge/`), matching the
final delivery layout:

- **Backend** (`agent-service/`) — alongside the provided `quote-service/`
  and `dataset/`. This is the graded core deliverable: the conversational
  agent itself.
- **Frontend** (`frontend/`) — the WhatsApp-style demo UI. Optional
  demonstration interface, not the primary evaluation criterion.

Repo layout: `agent-service/`, `frontend/`, `quote-service/`, `dataset/`,
`.ai/`, `CHALLENGE.md`, `README.md`, `docker-compose.yml`.

## Current scope — Backend (`agent-service`)

Current phase: **implemented, reviewed, and validated** — see
`.ai/project/reviews/final-backend-review.md` and
`final-validation-report.md` for the independent review/release-validation
passes and their evidence. Frontend integration against the real API is
also done (see below); `quote-service` and `dataset` remain unmodified per
the challenge brief.

Flow: `Frontend → Agent Service API → Conversation Orchestrator → LLM with
tool-calling → Quote Service Client → Existing Quote Service`.

Key decisions (see `architecture.md` for the structural detail):

- Language/framework: Python + FastAPI.
- LLM integration is provider-agnostic but minimally abstracted: one
  `LLMClient` Protocol, one OpenAI implementation, one factory keyed off
  `LLM_PROVIDER`/`LLM_MODEL`/`OPENAI_API_KEY` env vars. No hardcoded model
  or key. Adding another provider (e.g. Anthropic) later must not require
  touching orchestration or business logic.
- LLM-driven tool/function-calling, direct against a typed `quote-service`
  client — no MCP server (unnecessary infrastructure for one internal
  tool; revisit only if a concrete multi-tool/interoperability need
  appears).
- Conversation state is explicit application state (not LLM memory) —
  deterministic field-collection order, retry policy, and handoff policy,
  never left to LLM judgment.
- First version uses in-memory conversation storage behind an abstracted
  repository boundary — explicit known limitation, swappable later without
  touching orchestration logic.
- The quote-service is the sole source of truth for price and eligibility;
  the agent must never calculate, infer, or fabricate a price, and must
  never re-implement quote-service's business rules locally.

## Current scope — Frontend (`frontend/`)

Current phase: **wired to the real agent-service** via
`src/features/chat/useConversation.ts` + `api.ts`. The original offline
mock has been relocated to `src/demo/` (renamed `offlineMockAgent.ts` /
`useOfflineMockConversation.ts`), explicitly labeled as a non-production,
backend-free demo, and is no longer imported by any production component.

The frontend must:

- present a WhatsApp-style chat between a "lead" persona and the AutoSeguro
  agent: qualify → quote → decide (resolve or hand off to a human)
- simulate the agent's responses locally (mocked, deterministic) so every
  interface state is demonstrable without a running backend
- keep the mock conversation logic isolated from presentational components,
  so it can later be swapped for real calls to `quote-service` /
  a real agent backend without restructuring the UI
- handle loading, empty, success and error/failure states explicitly, since
  the real `/quote` endpoint is deliberately unreliable (this is the part of
  the challenge graded most closely)
- be responsive and accessible
- include relevant automated tests
- remain simple enough to explain and demo end-to-end

Backend integration is complete — see the backend scope above.

## Technology stack — Frontend

Confirmed, matches the existing `frontend/` scaffold:

- Language: TypeScript
- Framework: React 19
- Build tool: Vite
- Package manager: npm
- Styling: plain CSS (CSS custom properties for tokens, one stylesheet per
  component/feature, co-located with the component)
- Unit and component tests: Vitest + React Testing Library
- End-to-end tests: none at this stage

## Technology stack — Backend

- Language: Python (3.12+)
- Framework: FastAPI
- Data/config: pydantic v2, pydantic-settings
- HTTP client (quote-service integration): httpx (async)
- LLM SDK: `openai` (provider-agnostic `LLMClient` interface wraps it —
  see `architecture.md`)
- Logging: structlog (structured JSON logs)
- Testing: pytest, pytest-asyncio, respx/pytest-httpx for HTTP mocking
- Package/dependency management: uv (matches `quote-service`'s existing
  convention)
- Containerization: Dockerfile per service; the repo-root `docker-compose.yml`
  will gain an `agent-service` entry once the service is runnable

## Project commands — Frontend

Use only commands that exist in `package.json`.

```bash
npm install
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
```

## Project commands — Backend

Use only commands that exist in `agent-service/pyproject.toml`.

```bash
cd agent-service
uv sync
uv run uvicorn app.main:app --reload --port 8080
uv run pytest
```

Required env vars are documented in `agent-service/.env.example`
(`LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`, `QUOTE_SERVICE_BASE_URL`,
plus the timeout/retry settings in `architecture.md`). Never commit a real
`OPENAI_API_KEY` — the repo will be public.

## Squad config notes

Previously-stale cross-references have been fixed: `.ai/prompts/` and
`.ai/workflows/` now consistently reference `context.md` (not the
nonexistent `context.yaml`) and `.ai/workflows/` (not the misspelled
`.ai/worflows/`); `review-backeend.workflow.md` was renamed to
`review-backend.workflow.md` and its two referrers updated to match.

One remaining, intentional asymmetry: `.ai/prompts/` has no dedicated
`review-backend.md` / `validate-backend.md` prompt files (only the
frontend has prompt + workflow pairs for review and validate). The backend
review/validate workflows reference `.ai/agents/backend-dev.yaml` directly
instead — this works and is exercised (see
`.ai/project/reviews/final-backend-review.md`), just not symmetric with
the frontend's structure. Not fixed, since adding two prompt files that
would only restate what the workflow files already say isn't worth the
duplication.
