# Deployment Release Validation Workflow

Use this workflow after deployment preparation and code review, before submitting, merging, or demonstrating the deployed application.

## Purpose

Determine whether the repository is ready for local demonstration and/or hosted deployment using verifiable evidence.

This workflow does not replace deployment preparation or review. It confirms that the reviewed configuration satisfies delivery requirements.

Detailed validation criteria are defined in the referenced agent and prompt files.

## Required inputs

Provide:

* deployment readiness plan
* implementation report
* review report
* changed and created files or diff
* available project scripts and commands
* known limitations

The implementation should normally have a review assessment of:

* `Ready`
* `Ready with non-blocking suggestions`

A `Not ready` review must return to implementation before release validation.

## Context

Use:

* `.ai/agents/deployment-engineer.yaml`
* `.ai/prompts/implement-deploy.md`
* `.ai/project/context.md`

Read:

* the current changed and created files
* `docker-compose.yml` and every Dockerfile
* `.env.example` files
* README sections affected by the change
* configuration required to run the application locally and, if applicable, in hosted environments

## Execution

### Step 1 — Confirm delivery scope

Confirm:

* services included in the deployment preparation (frontend, agent-service, quote-service)
* whether hosted deployment or only local Docker Compose readiness is in scope
* configuration or environment-variable changes
* documented known limitations
* unresolved review suggestions

Flag unrelated or undocumented changes.

### Step 2 — Check repository hygiene

Inspect the delivery for:

* committed secrets or tokens (`OPENAI_API_KEY` or equivalent)
* `.env` files committed instead of ignored
* placeholder values missing from `.env.example`
* hardcoded production URLs or hardcoded localhost defaults in production paths
* demo or mock pricing reachable from a production configuration path
* dead or commented-out configuration
* accidental files (build artifacts, local caches) added to version control
* required behavior left as TODO
* unrelated modifications

Confirmed secret exposure must immediately block the release.

### Step 3 — Run automated validation

Run only the applicable commands defined in:

* `.ai/project/context.md`
* `.ai/prompts/implement-deploy.md`

For each command, record:

* exact command
* execution result
* relevant output
* failure classification
* whether it blocks delivery

Cover, at minimum:

* agent-service tests
* quote-service tests
* frontend tests, lint, and type checking, if configured
* frontend production build
* every Docker image build
* full stack startup via `docker compose up --build`

Do not change validation configuration merely to obtain a passing result.

### Step 4 — Validate local runtime behavior

When the environment supports runtime validation, verify:

* the documented `cp .env.example .env` + `docker compose up --build` flow actually works as written
* every health endpoint returns success
* the frontend is reachable and communicates only with the agent-service
* the agent-service is reachable and communicates with the quote-service
* the quote-service is not directly reachable from the browser
* one successful end-to-end quote flow
* one invalid or ineligible vehicle flow
* one failure, retry, or human-handoff flow
* one multi-message correction flow
* pricing in every scenario comes only from the quote-service, never fabricated

Compare the observed behavior directly with the deployment plan and acceptance criteria.

### Step 5 — Validate hosted deployment configuration (if in scope)

When hosted deployment configuration is part of this delivery, confirm without provisioning infrastructure:

* frontend hosting configuration (root directory, install/build commands, output directory, API URL environment variable) is correct for Vercel or the chosen target
* agent-service hosting configuration (start command, health-check path, required environment variables, OpenAI secret handling) is correct for Render/Railway or the chosen target
* quote-service hosting configuration (start command, health-check path, required environment variables) is correct
* no hosted resource was created, no billing was configured, and no domain was added without explicit prior user approval

### Step 6 — Validate security and privacy

Check the delivery for:

* exposed secrets or tokens in code, configuration, logs, or documentation
* the OpenAI API key reachable from any frontend-served code or bundle
* CORS configuration that is overly permissive for production
* stack traces or internal error details exposed through health or error responses
* sensitive request/response data logged in plain text

Any confirmed secret exposure or security issue blocks the release.

### Step 7 — Reconcile the review report

Confirm that:

* blocking review findings were resolved
* important findings were resolved or explicitly accepted
* non-blocking suggestions were either implemented or documented
* new changes introduced after review were also reviewed

When the implementation changed materially after the last review, return to:

* `.ai/workflows/review-deployment.workflow.md`

Do not validate a materially changed implementation using an outdated review report.

### Step 8 — Produce the release decision

Choose:

* `READY_FOR_DEPLOYMENT`
* `READY_WITH_LIMITATIONS`
* `NOT_READY`

The decision must be supported by the evidence collected during this workflow.

### Step 9 — Produce the validation report

Return:

### Release decision

Choose one and include a concise explanation:

* `READY_FOR_DEPLOYMENT`
* `READY_WITH_LIMITATIONS`
* `NOT_READY`

### Automated evidence

Commands executed, results and relevant output.

### Manual and runtime evidence

Behavior observed, scenarios verified (local Docker Compose startup, health checks, end-to-end quote flow, failure/handoff flow) and how they were checked.

### Code-inspection evidence

Findings confirmed by reading Dockerfiles, compose files, `.env.example` files, and configuration rather than running them.

### Unavailable evidence

Checks that could not be performed and the reason (for example, hosted-provider validation that requires provisioning not yet approved).

### Known limitations

Confirmed limitations that do not block delivery, with their documented impact.

---

## Release decision rules

### READY_FOR_DEPLOYMENT

Use when:

* mandatory local startup works exactly as documented
* applicable automated checks pass
* the primary quote flow, the failure/handoff flow, and the correction flow are verified end to end
* no secret is exposed anywhere in the repository or runtime output
* the browser cannot reach the quote-service directly
* no production path can serve demo or mock pricing
* no blocking review finding remains

### READY_WITH_LIMITATIONS

Use when:

* mandatory local startup and safety invariants hold
* remaining limitations are confirmed and documented (for example, hosted deployment not yet provisioned, cold-start behavior on free-tier hosting)
* limitations do not compromise secret safety, topology integrity, or pricing integrity
* delivery stakeholders can understand their impact

### NOT_READY

Use when any of the following remains:

* failed build or failed critical test
* broken local Docker Compose startup
* any committed or exposed secret
* the browser able to reach the quote-service directly
* any path that can serve demo or mock pricing in production
* unresolved blocking review finding
* insufficient evidence to establish that mandatory deployment behavior works

## Completion criteria

This workflow is complete when:

* delivery scope has been confirmed
* applicable automated checks have been executed
* local runtime behavior has been verified against the documented evaluator flow
* hosted deployment configuration has been assessed, when in scope
* secret exposure and topology integrity have been confirmed
* review findings have been reconciled
* evidence gaps have been documented
* a release decision has been produced

## Handoff rules

### READY_FOR_DEPLOYMENT

The deployment preparation may proceed to submission, merge, demonstration, or — with explicit user approval — hosted provisioning.

### READY_WITH_LIMITATIONS

The deployment preparation may proceed only with the documented limitations included in the delivery notes.

### NOT_READY

Return to:

1. `.ai/workflows/implement-deployment.workflow.md`
2. `.ai/workflows/review-deployment.workflow.md`
3. this validation workflow

Execute only the stages affected by the correction, but do not skip review when the correction materially changes the implementation.

## Integrity rules

* Never report an unexecuted command as successful.
* Never report an untested startup flow as validated.
* Never omit relevant failing output.
* Never downgrade a secret-exposure or topology-safety issue to a known limitation.
* Never mark a release as ready when mandatory evidence is unavailable.
* Never treat implementation confidence as a substitute for validation evidence.
* Never provision hosted infrastructure, configure billing, or add domains without explicit prior user approval.
