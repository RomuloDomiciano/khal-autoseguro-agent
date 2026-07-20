# Implement Backend

Act as the agent defined in:

* `.ai/agents/backend-dev.yaml`

Read:

* `.ai/project/context.md`
* `.ai/project/architecture.md`
* the current task and acceptance criteria
* only the source files directly related to the requested change
* existing routes, adapters, services, domain types and tests that may be reused

## Objective

Implement the smallest complete backend change that satisfies the acceptance criteria while preserving the project's architecture, conventions and existing behavior.

## Before implementation

Briefly report:

* your understanding of the requested behavior
* relevant assumptions
* affected files or areas
* happy path, failure, retry and handoff states that apply
* the proposed implementation approach

Keep this analysis proportional to the task.

## Implementation rules

* Follow the existing project conventions.
* Reuse existing adapters, services and utilities when appropriate.
* Keep changes focused on the requested scope.
* Separate route handlers from business orchestration.
* Isolate the quote-service behind a client or adapter layer.
* Keep handoff policy in a dedicated module or policy layer.
* Keep prompt construction separate from infrastructure code.
* Use typed contracts for domain objects; avoid untyped dictionaries for core models.
* Classify errors explicitly — distinguish transient from non-retryable failures.
* Apply explicit request timeouts on all external calls.
* Retry only transient failures, with bounded attempts and backoff.
* Never calculate, infer or fabricate a quotation price locally.
* Never present a price that was not successfully returned by the quote-service.
* Record a machine-readable reason for every human handoff.
* Preserve conversation continuity using a stable `conversation_id`.
* Propagate a `request_id` or correlation identifier for external calls.
* Use structured logs; do not log raw CPF, phone, e-mail, address or other personal fields.
* Do not expose stack traces or internal error details to the lead.
* Do not add infrastructure complexity (queues, brokers, distributed systems) without a demonstrated need.
* Do not add dependencies unless clearly justified.
* Do not modify the provided quote-service unless explicitly required.
* Add or update tests for relevant behavior.
* Do not modify unrelated files.

## Validation

Run only the applicable commands defined in `.ai/project/context.md`.

Never claim that a command, test or manual check was performed when it was not.

## Final response

Return:

### Summary

What was implemented and how it affects the system's behavior.

### Files changed

Each created or modified file with a brief explanation.

### Validation

Commands and checks actually performed, including failures or checks that could not be completed.

### Assumptions

Only assumptions that materially affected the implementation.

### Risks and limitations

Confirmed remaining risks or limitations. Do not invent optional future work.
