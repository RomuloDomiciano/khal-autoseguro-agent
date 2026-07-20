# Frontend Release Validation Workflow

Use this workflow after implementation and code review, before submitting, merging or demonstrating the frontend application.

## Purpose

Determine whether the frontend change is ready for delivery using verifiable evidence.

This workflow does not replace implementation or code review. It confirms that the reviewed implementation satisfies the delivery requirements.

Detailed validation criteria are defined in the validation prompt.

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

* `.ai/prompts/validate-frontend.md`
* `.ai/project/context.md`

Load `.ai/agents/frontend-dev.yaml` only when an implementation decision must be reassessed.

Read:

* the current changed files
* relevant tests
* project scripts
* configuration required to execute the application
* documentation affected by the change

## Execution

### Step 1 — Confirm delivery scope

Confirm:

* features included in the delivery
* mandatory acceptance criteria
* affected user flows
* configuration changes
* dependency changes
* documented known limitations
* unresolved review suggestions

Flag unrelated or undocumented changes.

### Step 2 — Check repository hygiene

Inspect the delivery for:

* temporary logs
* debug flags
* placeholder values
* hardcoded local URLs
* commented-out implementations
* exposed secrets
* accidental files
* missing environment variable documentation
* required behavior left as TODO
* unrelated modifications

Confirmed secret exposure must immediately block the release.

### Step 3 — Run automated validation

Run only the applicable commands defined in:

* `.ai/project/context.md`

Use the command order defined by the project.

For each command, record:

* exact command
* execution result
* relevant output
* failure classification
* whether it blocks delivery

Do not change validation configuration merely to obtain a passing result.

### Step 4 — Validate functional behavior

When the environment supports runtime validation, verify:

* the primary user flow
* applicable alternate flows
* loading behavior
* successful completion
* empty states
* invalid input
* network or server failure
* retry behavior
* duplicate-action prevention
* recovery after a recoverable failure

Compare the observed behavior directly with the acceptance criteria.

### Step 5 — Validate accessibility

Perform the applicable checks defined in:

* `.ai/prompts/validate-frontend.md`

Distinguish between:

* checks actually performed
* checks supported only by code inspection
* checks that could not be performed

Automated accessibility tools do not replace keyboard and focus validation when manual validation is available.

### Step 6 — Validate security and privacy

Check the delivery for:

* exposed secrets
* sensitive data in logs
* unsafe persistence of tokens or user data
* unsafe rendering of external content
* internal error details exposed to users
* client-side behavior incorrectly treated as authorization
* changes that weaken authentication or authorization flows

Any confirmed sensitive-data exposure or authorization bypass blocks the release.

### Step 7 — Reconcile the review report

Confirm that:

* blocking review findings were resolved
* important findings were resolved or explicitly accepted
* non-blocking suggestions were either implemented or documented
* new changes introduced after review were also reviewed

When the implementation changed materially after the last review, return to:

* `.ai/workflows/review-frontend.workflow.md`

Do not validate a materially changed implementation using an outdated review report.

### Step 8 — Produce the release decision

Use the decision rules defined in:

* `.ai/prompts/validate-frontend.md`

Choose:

* `Ready`
* `Ready with known limitations`
* `Not ready`

The decision must be supported by the evidence collected during this workflow.

### Step 9 — Produce the validation report

Return the response format defined in:

* `.ai/prompts/validate-frontend.md`

The report must clearly separate:

* automated evidence
* manual evidence
* code-inspection evidence
* unavailable evidence

## Release decision rules

### Ready

Use when:

* mandatory acceptance criteria are satisfied
* applicable automated checks pass
* the primary flow is verified
* no blocking security or accessibility issue remains
* no blocking review finding remains
* no material evidence gap prevents a delivery decision

### Ready with known limitations

Use when:

* mandatory behavior is valid
* remaining limitations are confirmed and documented
* limitations do not compromise correctness, security or mandatory accessibility
* limitations do not violate acceptance criteria
* delivery stakeholders can understand their impact

### Not ready

Use when any of the following remains:

* failed build
* failed critical test
* broken primary flow
* unmet mandatory acceptance criterion
* confirmed security issue
* exposed sensitive data
* unresolved blocking review finding
* major accessibility barrier in the primary flow
* insufficient evidence to establish that mandatory behavior works

## Completion criteria

This workflow is complete when:

* delivery scope has been confirmed
* applicable automated checks have been executed
* available manual checks have been performed
* security and accessibility have been assessed
* review findings have been reconciled
* evidence gaps have been documented
* a release decision has been produced

## Handoff rules

### Ready

The frontend change may proceed to submission, merge or demonstration.

### Ready with known limitations

The frontend change may proceed only with the documented limitations included in the delivery notes.

### Not ready

Return to:

1. `.ai/workflows/implement-frontend.workflow.md`
2. `.ai/workflows/review-frontend.workflow.md`
3. this validation workflow

Execute only the stages affected by the correction, but do not skip review when the correction materially changes the implementation.

## Integrity rules

* Never report an unexecuted command as successful.
* Never report an untested browser or viewport as validated.
* Never omit relevant failing output.
* Never downgrade a security issue to a known limitation.
* Never mark a release as ready when mandatory evidence is unavailable.
* Never use implementation confidence as a substitute for validation evidence.
