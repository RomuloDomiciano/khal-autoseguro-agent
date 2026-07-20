# Frontend Change Review Workflow

Use this workflow after frontend implementation and before release validation.

## Purpose

Perform an independent review of the frontend change without modifying the implementation.

The review must focus on evidence-based defects, regressions and meaningful engineering risks.

Detailed review rules are defined in the referenced agent and review prompt.

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

* `.ai/agents/frontend-dev.yaml`
* `.ai/prompts/review-frontend.md`
* `.ai/project/context.md`

Read:

* the changed files
* the surrounding code necessary to understand them
* relevant tests
* relevant contracts and types

Avoid loading unrelated areas of the repository.

## Execution

### Step 1 — Establish review scope

Identify:

* intended user behavior
* acceptance criteria
* changed files
* affected flows
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

Apply the review priorities defined in:

* `.ai/prompts/review-frontend.md`

Review in this order:

1. functional correctness
2. security and sensitive-data exposure
3. accessibility
4. interface states and error handling
5. architecture and maintainability
6. tests
7. evidence-based performance risks

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

Use the assessment rules from:

* `.ai/prompts/review-frontend.md`

Choose:

* `Ready`
* `Ready with non-blocking suggestions`
* `Not ready`

A change must be classified as `Not ready` when at least one confirmed blocking issue remains.

### Step 6 — Produce the review report

Return the response format defined in:

* `.ai/prompts/review-frontend.md`

The review report becomes an input for release validation.

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

* `.ai/workflows/validate-frontend.workflow.md`

### Ready with non-blocking suggestions

Continue to release validation.

Suggestions may be deferred when they do not affect:

* acceptance criteria
* safety
* correctness
* accessibility of the primary flow
* maintainability required for delivery

### Not ready

Return the implementation to the implementation workflow.

Provide the blocking and important findings as implementation inputs.

After correction, execute this review workflow again.

## Stop conditions

Stop the review and report insufficient evidence when:

* the changed files or diff are unavailable
* acceptance criteria are unavailable and intended behavior cannot be inferred
* required generated code or external contract cannot be inspected
* the reviewer cannot distinguish the current change from unrelated repository changes

Do not approve a change when the available evidence is insufficient.
