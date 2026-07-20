# Frontend Feature Implementation Workflow

Use this workflow to implement a new frontend feature or modify existing frontend behavior.

## Purpose

Coordinate the implementation process using the frontend engineering agent and the implementation prompt.

This workflow defines the execution sequence. Detailed implementation rules are defined in the referenced agent and prompt files.

## Required inputs

Before starting, ensure the following information is available:

* task description
* expected user behavior
* acceptance criteria
* relevant design or interface reference, when applicable
* API contract or expected data structure, when applicable

Do not invent missing business requirements.

When information is incomplete but a safe implementation decision can be made, document the assumption.

## Context

Use:

* `.ai/agents/frontend-dev.yaml`
* `.ai/prompts/implement-frontend.md`
* `.ai/project/context.md`

Read only the source files necessary to understand and implement the requested feature.

## Execution

### Step 1 — Understand the task

Use the implementation prompt to:

* summarize the requested behavior
* identify the acceptance criteria
* identify assumptions
* identify the affected areas
* identify relevant interface states

Do not modify code during this step.

### Step 2 — Inspect the existing implementation

Inspect:

* the feature entry point
* related pages and components
* existing services and hooks
* shared types and schemas
* related tests
* existing styling and state-management conventions

Prefer existing project patterns over introducing new structures.

### Step 3 — Define the implementation plan

Create a short plan containing:

* files to create
* files to modify
* components or services affected
* tests to add or update
* validation commands to run

The plan must remain proportional to the task.

### Step 4 — Implement

Execute the plan using the instructions in:

* `.ai/agents/frontend-dev.yaml`
* `.ai/prompts/implement-frontend.md`

Keep the changes focused on the requested behavior.

When the implementation requires an architectural decision, document the decision before applying it.

### Step 5 — Perform implementation self-review

Before running validation:

* inspect the complete change
* compare it with the acceptance criteria
* remove temporary code
* verify that no unrelated files were modified
* verify that relevant interface states are handled
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

* `.ai/prompts/implement-frontend.md`

The implementation report becomes the input for the review workflow.

## Completion criteria

This workflow is complete when:

* the requested behavior has been implemented
* the acceptance criteria have been reviewed
* relevant tests have been added or updated
* applicable validation commands have been executed
* implementation risks and limitations have been documented
* the implementation report has been produced

Completion of this workflow does not mean the change is approved for delivery.

The change must still pass:

1. `review-frontend.workflow.md`
2. `validate-frontend.workflow.md`

## Stop conditions

Stop implementation and report the blocker when:

* a required API or data contract is unavailable
* the requested behavior creates a confirmed security risk
* the task requires backend behavior that does not exist
* mandatory requirements conflict with each other
* the requested change would require an unjustified modification outside the task scope
* the project cannot be safely modified without additional context

Do not use a stop condition for minor ambiguity that can be resolved through a documented, low-risk assumption.
