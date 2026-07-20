# Backend Release Validation Workflow

Use this workflow after implementation and code review, before submitting, merging or demonstrating the backend application.

## Purpose

Determine whether the backend change is ready for delivery using verifiable evidence.

This workflow does not replace implementation or code review. It confirms that the reviewed implementation satisfies the delivery requirements.

Detailed validation criteria are defined in the referenced agent and prompt files.

## Required inputs

Provide:

* task description
* acceptance criteria
* implementation report
* review report
* changed files or diff
* available project scripts
* relevant tests
* known limitations

The implementation should normally have a review assessment of:

* `Ready`
* `Ready with non-blocking suggestions`

A `Not ready` review must return to implementation before release validation.

## Context

Use:

* `.ai/agents/backend-dev.yaml`
* `.ai/project/context.md`
* `.ai/project/architecture.md`

Read:

* the current changed files
* relevant tests
* project scripts
* configuration and environment variables required to run the application
* documentation affected by the change

## Execution

### Step 1 — Confirm delivery scope

Confirm:

* features included in the delivery
* mandatory acceptance criteria
* affected flows (qualification, quotation, retry, handoff)
* configuration or environment-variable changes
* dependency changes
* documented known limitations
* unresolved review suggestions

Flag unrelated or undocumented changes.

### Step 2 — Check repository hygiene

Inspect the delivery for:

* temporary logs or debug output
* dead or commented-out implementations
* hardcoded secrets, tokens or environment-specific URLs
* placeholder or fabricated values in the quotation path
* exposed sensitive fields (CPF, phone, e-mail, address)
* missing environment-variable documentation
* required behavior left as TODO
* unrelated modifications
* accidental files

Confirmed secret or sensitive-data exposure must immediately block the release.

### Step 3 — Run automated validation

Run only the applicable commands defined in:

* `.ai/project/context.md`

For each command, record:

* exact command
* execution result
* relevant output
* failure classification
* whether it blocks delivery

Do not change validation configuration merely to obtain a passing result.

### Step 4 — Validate functional behavior

When the environment supports runtime validation, verify:

* the qualification flow (agent collects required fields)
* the successful quotation path (response comes only from quote-service)
* transient failure handling (timeout, 502, 503 — retried, not fabricated)
* retry exhaustion (graceful response, handoff triggered where applicable)
* non-retryable failure handling (400, 422 — not retried)
* human handoff (explicit reason, user-safe message)
* `conversation_id` and correlation identifiers present in logs
* quotation status recorded after each attempt
* no price fabricated on any failure path

Compare the observed behavior directly with the acceptance criteria.

### Step 5 — Validate resilience

Confirm the following against the implementation or by running targeted tests:

* all external requests have explicit timeouts
* retries are bounded (not infinite)
* only transient failures are retried (connection error, timeout, 502, 503, 504)
* non-retryable failures (400, 422, 401, 403, 404) are not retried
* backoff is applied between retry attempts
* retry exhaustion produces a safe user response or handoff
* duplicate quotation requests are controlled where the operation is non-idempotent
* no infrastructure failure results in a fabricated or estimated price

### Step 6 — Validate observability

Confirm that the following fields are traceable in logs or persisted state:

* `conversation_id`
* `request_id` or correlation identifier for external calls
* quotation status per attempt
* retry attempt count
* handoff reason and status
* external-call latency or failure code

Confirm that the following fields are **not** logged in plain text:

* CPF
* phone number
* e-mail
* home address
* financial data

### Step 7 — Validate handoff behavior

Confirm that every human handoff:

* has a machine-readable reason present in the defined policy
* includes a user-safe explanation delivered to the lead
* preserves a conversation summary for the human operator
* does not invent a temporary quotation
* distinguishes technical handoff from business handoff

### Step 8 — Validate security and privacy

Check the delivery for:

* exposed secrets or tokens
* sensitive data in structured logs
* stack traces or internal error details returned to users
* personal data sent to an LLM unnecessarily
* unsafe persistence of conversation data
* missing or incorrectly documented environment variables

Any confirmed sensitive-data exposure or security issue blocks the release.

### Step 9 — Reconcile the review report

Confirm that:

* blocking review findings were resolved
* important findings were resolved or explicitly accepted
* non-blocking suggestions were either implemented or documented
* new changes introduced after review were also reviewed

When the implementation changed materially after the last review, return to:

* `.ai/workflows/review-backend.workflow.md`

Do not validate a materially changed implementation using an outdated review report.

### Step 10 — Produce the release decision

Choose:

* `Ready`
* `Ready with known limitations`
* `Not ready`

The decision must be supported by the evidence collected during this workflow.

### Step 11 — Produce the validation report

Return:

### Release decision

Choose one and include a concise explanation:

* Ready
* Ready with known limitations
* Not ready

### Automated evidence

Commands executed, results and relevant output.

### Manual and runtime evidence

Behavior observed, scenarios verified and how they were checked.

### Code-inspection evidence

Findings confirmed by reading the implementation rather than running it.

### Unavailable evidence

Checks that could not be performed and the reason.

### Known limitations

Confirmed limitations that do not block delivery, with their documented impact.

---

## Release decision rules

### Ready

Use when:

* mandatory acceptance criteria are satisfied
* applicable automated checks pass
* the primary quotation flow is verified end to end
* no quotation price can be fabricated on any tested failure path
* no blocking security or data-protection issue remains
* no blocking review finding remains
* resilience and handoff behavior are confirmed

### Ready with known limitations

Use when:

* mandatory behavior is valid
* remaining limitations are confirmed and documented
* limitations do not compromise quotation integrity, security or mandatory handoff behavior
* limitations do not violate acceptance criteria
* delivery stakeholders can understand their impact

### Not ready

Use when any of the following remains:

* failed build
* failed critical test
* broken primary quotation flow
* any path that can fabricate or present an unconfirmed price
* unmet mandatory acceptance criterion
* confirmed security issue or sensitive-data exposure
* unresolved blocking review finding
* missing handoff reason or user-safe message
* insufficient evidence to establish that mandatory behavior works

## Completion criteria

This workflow is complete when:

* delivery scope has been confirmed
* applicable automated checks have been executed
* available runtime checks have been performed
* quotation integrity has been confirmed on failure paths
* resilience and handoff behavior have been assessed
* security and privacy have been assessed
* review findings have been reconciled
* evidence gaps have been documented
* a release decision has been produced

## Handoff rules

### Ready

The backend change may proceed to submission, merge or demonstration.

### Ready with known limitations

The backend change may proceed only with the documented limitations included in the delivery notes.

### Not ready

Return to:

1. `.ai/workflows/implement-backend.workflow.md`
2. `.ai/workflows/review-backend.workflow.md`
3. this validation workflow

Execute only the stages affected by the correction, but do not skip review when the correction materially changes the implementation.

## Integrity rules

* Never report an unexecuted command as successful.
* Never report an untested failure scenario as validated.
* Never omit relevant failing output.
* Never downgrade a security or data-protection issue to a known limitation.
* Never mark a release as ready when mandatory evidence is unavailable.
* Never treat implementation confidence as a substitute for validation evidence.
* Never accept a fabricated price as a known limitation.
