# Offline demo — not production

This folder is a fully client-side, backend-free conversation simulator kept
only so the chat UI can be demoed or screenshotted without running
`agent-service` or `quote-service`. It is not imported by any production
code path.

The real app lives in `../features/chat/` and talks to the real
agent-service via `useConversation.ts` / `api.ts`. **Only that path is the
source of truth for price and eligibility.**

`offlineMockAgent.ts` duplicates `quote-service/data/plans.json`'s pricing
rules as they were at the time this was written, and will drift out of sync
over time. Never use this folder's output to inform a real quote.
