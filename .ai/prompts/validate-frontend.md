# Validate Frontend Delivery

Act as the agent defined in:

* `.ai/agents/frontend-dev.yaml`

Read:

* `.ai/project/context.md`
* the task and acceptance criteria
* the current changed files
* relevant tests
* the scripts available in the project

## Objective

Determine whether the frontend implementation is ready for delivery using evidence from automated checks, code inspection and available manual validation.

Do not change the implementation unless explicitly requested.

## Validation scope

Validate what is applicable:

### Requirements

* mandatory acceptance criteria are satisfied
* the primary user flow is complete
* relevant alternate and failure flows are handled
* no mock, placeholder or temporary behavior remains unintentionally

### Repository hygiene

* no temporary logs
* no dead or commented-out implementation
* no accidental generated files
* no hardcoded local URLs
* no exposed secrets
* no unrelated changes
* required environment variables are documented

### Automated checks

Run the applicable commands defined in `.ai/project/context.md`, such as:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

Run only commands that exist in the project.

For every command, record:

* exact command
* result
* relevant failure
* whether the failure blocks delivery

### Functional behavior

When the environment allows, verify:

* initial state
* loading state
* success state
* empty state
* invalid input
* network or server failure
* retry behavior
* duplicate-action prevention
* preservation of user input after recoverable failures

### Accessibility

Check, when possible:

* keyboard navigation
* visible and logical focus
* accessible labels and control names
* semantic structure
* error identification
* interactions that do not depend only on color or pointer hover

### Security and privacy

Confirm that:

* no secret is exposed in client code
* no sensitive data is unnecessarily persisted or logged
* untrusted HTML is not rendered unsafely
* internal errors are not exposed to users
* client-side visibility is not treated as authorization

## Release decision

Choose one:

* `Ready`: mandatory checks passed and no blocking issue remains
* `Ready with known limitations`: mandatory behavior is valid and remaining limitations are documented and non-blocking
* `Not ready`: a blocking failure or unmet mandatory requirement remains

A failed build, critical test failure, broken primary flow, sensitive-data exposure or unmet mandatory acceptance criterion must result in `Not ready`.

## Final response

Return:

### Decision

Ready, Ready with known limitations, or Not ready.

### Scope validated

Features and acceptance criteria covered.

### Automated checks

Commands actually executed and their results.

### Manual checks

Behavior actually verified.

### Accessibility

Checks performed and findings.

### Security and privacy

Checks performed and findings.

### Blocking issues

Unresolved blockers, or state that none were found.

### Known limitations

Confirmed non-blocking limitations.

### Evidence gaps

Anything that could not be validated in the available environment.

Never report a test, command, browser, viewport or interaction as validated unless it was actually checked.
