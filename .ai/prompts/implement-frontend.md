# Implement Frontend

Act as the agent defined in:

* `.ai/agents/frontend-dev.yaml`

Read:

* `.ai/project/context.md`
* the current task and acceptance criteria
* only the source files directly related to the requested change
* existing components, services, types and tests that may be reused

## Objective

Implement the smallest complete frontend change that satisfies the acceptance criteria while preserving the project's architecture, conventions and existing behavior.

## Before implementation

Briefly report:

* your understanding of the requested behavior
* relevant assumptions
* affected files or areas
* loading, empty, success and error states that apply
* the proposed implementation approach

Keep this analysis proportional to the task.

## Implementation rules

* Follow the existing project conventions.
* Reuse existing components and utilities when appropriate.
* Keep changes focused on the requested scope.
* Preserve strong typing.
* Keep API communication outside presentational components.
* Do not place complex business rules inside UI components.
* Handle applicable asynchronous and failure states.
* Use semantic and keyboard-accessible interactions.
* Do not add dependencies unless clearly justified.
* Do not expose secrets or sensitive data.
* Add or update tests for relevant user behavior.
* Do not modify unrelated files.

## Validation

Run only the applicable commands defined in `.ai/project/context.md`.

Never claim that a command, test or manual check was performed when it was not.

## Final response

Return:

### Summary

What was implemented and how it affects the user.

### Files changed

Each created or modified file with a brief explanation.

### Validation

Commands and checks actually performed, including failures or checks that could not be completed.

### Assumptions

Only assumptions that materially affected the implementation.

### Risks and limitations

Confirmed remaining risks or limitations. Do not invent optional future work.
