# Backend Feature Implementation Workflow

Use this workflow to implement a new backend feature or modify existing backend behavior.

## Purpose

Coordinate the implementation process using the backend engineering agent and the implementation prompt.

This workflow defines the execution sequence. Detailed implementation rules are defined in the referenced agent and prompt files.

## Required inputs

Before starting, ensure the following information is available:

* task description
* expected system behavior
* acceptance criteria
* relevant API contract or data structure, when applicable
* quote-service endpoint contracts, when the change touches quotation

Do not invent missing business requirements.

When information is incomplete but a safe implementation decision can be made, document the assumption.

## Context

Use:

* `.ai/agents/backend-dev.yaml`
* `.ai/prompts/implement-backend.md`
* `.ai/project/context.md`
* `.ai/project/architecture.md`

Read only the source files necessary to understand and implement the requested change.

## Execution

### Step 1 — Understand the task

Use the implementation prompt to:

* summarize the requested behavior
* identify the acceptance criteria
* identify assumptions
* identify the affected areas
* identify happy path, failure, retry and handoff states that apply

Do not modify code during this step.

### Step 2 — Inspect the existing implementation

Inspect:

* the feature entry point (route handler or controller)
* related orchestration and service layers
* existing adapters and clients for external dependencies
* shared domain types and error models
* handoff policy modules
* related tests
* existing logging and observability conventions

Prior to touching quotation behavior, inspect `GET /planos` from the quote-service to understand current plan rules.

Prefer existing project patterns over introducing new structures.

### Step 3 — Define the implementation plan

Create a short plan containing:

* files to create
* files to modify
* services or adapters affected
* retry, timeout and handoff decisions required
* traceability fields to propagate
* tests to add or update
* validation commands to run

The plan must remain proportional to the task.

### Step 4 — Implement

Execute the plan using the instructions in:

* `.ai/agents/backend-dev.yaml`
* `.ai/prompts/implement-backend.md`

Keep the changes focused on the requested behavior.

When the implementation requires an architectural decision, document the decision before applying it.

Verify that:

* no quotation price is calculated or fabricated locally
* all external requests have explicit timeouts
* retries are bounded and applied only to transient failures
* every human handoff records a machine-readable reason
* sensitive fields are not logged in plain text

### Step 5 — Perform implementation self-review

Before running validation:

* inspect the complete change
* compare it with the acceptance criteria
* verify that no price is fabricated on any failure path
* verify retry limits, timeout values and backoff behavior
* verify handoff reasons and user-facing messages
* verify that `conversation_id` and correlation identifiers are propagated
* remove temporary code
* verify that no unrelated files were modified
* verify that the implementation follows existing project conventions

Correct relevant findings before continuing.

### Step 6 — Run implementation validation

Run the applicable commands defined in:

* `.ai/project/context.md`

Record:

* commands executed
* successful commands
* failed commands
* validations that could not be performed

Do not hide failures or claim that an unexecuted command passed.

### Step 7 — Produce the implementation report

Return the response format defined in:

* `.ai/prompts/implement-backend.md`

The implementation report becomes the input for the review workflow.
