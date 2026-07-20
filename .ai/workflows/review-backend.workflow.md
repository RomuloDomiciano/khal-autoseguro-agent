# Backend Change Review Workflow

Use this workflow after backend implementation and before release validation.

## Purpose

Perform an independent review of the backend change without modifying the implementation.

The review must focus on evidence-based defects, regressions and meaningful engineering risks. The highest-priority invariant is that the system must never invent or present a quotation price that was not successfully returned by the quote-service.

Detailed review rules are defined in the referenced agent and prompt files.

## Required inputs

Provide:

* task description
* acceptance criteria
* implementation report
* changed files or diff
* relevant tests
* validation results already produced during implementation

The reviewer must not assume that the implementation report is correct. It is supporting context, not evidence of correctness.

## Context

Use:

* `.ai/agents/backend-dev.yaml`
* `.ai/project/context.md`
* `.ai/project/architecture.md`

Read:

* the changed files
* the surrounding code necessary to understand them
* relevant tests
* relevant domain types and error models
* quote-service contracts when quotation behavior changed

Avoid loading unrelated areas of the repository.

## Execution

### Step 1 — Establish review scope

Identify:

* intended system behavior
* acceptance criteria
* changed files
* affected flows (qualification, quotation, retry, handoff)
* existing behavior that must be preserved
* validations already performed

State any interpretation used when the intended behavior is not completely explicit.

### Step 2 — Inspect the complete change

Review the complete diff before reviewing isolated files.

Look for:

* unintended changes
* incomplete implementations
* duplicated behavior
* inconsistent patterns
* changes outside the requested scope

### Step 3 — Review by priority

Review in this order:

1. Quotation integrity — no price can be fabricated, inferred or returned without a valid quote-service response
2. Resilience — timeouts, bounded retries, failure classification, no silent swallowing of external errors
3. Human handoff — explicit criteria, machine-readable reason, user-safe message, preserved conversation summary
4. Security and sensitive-data exposure — no PII in logs, no stack traces to the user, secrets not hardcoded
5. Functional correctness and acceptance criteria
6. Traceability — `conversation_id`, correlation identifiers, quotation status, retry counts
7. Architecture and maintainability — separation of concerns, typed contracts, no mixed layers
8. Test coverage
9. Evidence-based performance risks

Do not prioritize formatting or personal coding preferences over functional risks.

### Step 4 — Verify each finding

Before reporting a finding, confirm that it includes:

* affected file or behavior
* evidence from the implementation
* explanation of the defect or risk
* likely impact
* concrete recommendation
* appropriate severity

Do not report speculative findings without a plausible failure scenario.

### Step 5 — Classify the change

Use the severity definitions from:

* `.ai/agents/backend-dev.yaml` — `reviewSeverity`

Choose:

* `Ready`
* `Ready with non-blocking suggestions`
* `Not ready`

A change must be classified as `Not ready` when at least one confirmed blocking issue remains.

Blocking issues include any path that can fabricate a quotation, expose sensitive data, bypass handoff policy, corrupt conversation state or break the primary flow.

### Step 6 — Produce the review report

Return:

### Assessment

Choose one:

* Ready
* Ready with non-blocking suggestions
* Not ready

Include a concise explanation.

### Blocking issues

Evidence-based blocking findings, or state that none were found.

### Important issues

Evidence-based important findings, or state that none were found.

### Suggestions

Optional improvements, or state that none were found.

### Positive observations

Notable strengths in the implementation, if any.

### Validation gaps

Checks that could not be performed and the reason.

---

## Review independence

The reviewer must:

* inspect the implementation rather than trust the implementation summary
* avoid rewriting code unless explicitly requested
* avoid reducing severity to protect the implementation
* avoid increasing severity to make the review appear more rigorous
* distinguish confirmed defects from optional improvements
* report missing evidence as a validation gap

## Completion criteria

This workflow is complete when:

* the complete change has been inspected
* relevant tests have been reviewed
* findings have supporting evidence
* findings have been classified by severity
* an overall assessment has been produced
* validation gaps have been documented

## Handoff rules

### Ready

Continue to:

* `.ai/workflows/validate-backend.workflow.md`

### Ready with non-blocking suggestions

Continue to release validation.

Suggestions may be deferred when they do not affect:

* acceptance criteria
* quotation integrity
* resilience or handoff safety
* sensitive-data protection
* correctness of the primary flow

### Not ready

Return the implementation to the implementation workflow.

Provide the blocking and important findings as implementation inputs.

After correction, execute this review workflow again.

## Stop conditions

Stop the review and report insufficient evidence when:

* the changed files or diff are unavailable
* acceptance criteria are unavailable and intended behavior cannot be inferred
* required external contracts cannot be inspected
* the reviewer cannot distinguish the current change from unrelated repository changes

Do not approve a change when the available evidence is insufficient.
