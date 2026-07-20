# Deployment Change Review Workflow

Use this workflow after deployment preparation and before release validation.

## Purpose

Perform an independent review of the deployment preparation without modifying the implementation.

The review must focus on evidence-based defects, regressions and meaningful engineering risks. The highest-priority invariants are that no secret is exposed, the browser never reaches the quote-service directly, and production configuration never falls back to demo or mock pricing.

Detailed review rules are defined in the referenced agent and prompt files.

## Required inputs

Provide:

* deployment readiness plan
* implementation report (`.ai/workflows/implement-deployment.workflow.md` output)
* changed files or diff
* created files (Dockerfiles, compose files, `.env.example`, CI/deploy configuration)
* validation commands and results already produced during implementation

The reviewer must not assume that the implementation report is correct. It is supporting context, not evidence of correctness.

## Context

Use:

* `.ai/agents/deployment-engineer.yaml`
* `.ai/prompts/implement-deploy.md`
* `.ai/project/context.md`

Read:

* the changed and created files
* `docker-compose.yml` and every Dockerfile
* `.env.example` files for every service
* README sections affected by the change
* health-check implementations
* CORS and service-URL configuration

Avoid loading unrelated areas of the repository.

## Execution

### Step 1 — Establish review scope

Identify:

* intended deployment topology (frontend → agent-service → quote-service, OpenAI reachable only from agent-service)
* files created or modified
* hosting targets addressed (local Docker Compose, Vercel, Render/Railway)
* existing behavior that must be preserved
* validations already performed
* explicit user approvals already obtained for any hosted-infrastructure action

State any interpretation used when the intended configuration is not completely explicit.

### Step 2 — Inspect the complete change

Review the complete diff before reviewing isolated files.

Look for:

* unintended changes to application code or business logic
* incomplete Dockerfiles (missing `EXPOSE`, missing non-root user where relevant, missing production dependencies)
* duplicated or inconsistent service definitions in `docker-compose.yml`
* inconsistent patterns across services
* changes outside the requested deployment scope

### Step 3 — Review by priority

Review in this order:

1. Secret and credential exposure — no committed secrets, `.env` files ignored, `.env.example` contains placeholders only, `OPENAI_API_KEY` never reachable from the frontend
2. Topology integrity — the browser calls only the agent-service, the quote-service is not publicly exposed to the browser, the quote-service remains the only source of truth for prices
3. Production pricing integrity — no demo or mock pricing path is reachable in production configuration
4. Health and startup correctness — health endpoints are correctly wired, startup commands match the actual project (not assumed conventions), containers start cleanly
5. Configuration portability — CORS origins, service URLs, and timeouts are environment-driven rather than hardcoded to localhost
6. Reversibility and safety — no unapproved Git remote changes, no unapproved hosted-resource creation, no destructive or irreversible action taken without approval
7. Documentation accuracy — README instructions match the actual commands and file paths in the repository
8. Evidence quality — validations claimed in the implementation report are plausible and specific, not generic

Do not prioritize formatting or personal preferences over deployment-safety risks.

### Step 4 — Verify each finding

Before reporting a finding, confirm that it includes:

* affected file or configuration
* evidence from the implementation
* explanation of the defect or risk
* likely impact (e.g., secret leak, direct quote-service exposure, broken evaluator startup)
* concrete recommendation
* appropriate severity

Do not report speculative findings without a plausible failure scenario.

### Step 5 — Classify the change

Choose:

* `Ready`
* `Ready with non-blocking suggestions`
* `Not ready`

A change must be classified as `Not ready` when at least one confirmed blocking issue remains.

Blocking issues include any path that exposes a secret, allows the browser to bypass the agent-service, allows production to serve mock or fabricated pricing, or leaves the documented local startup command non-functional.

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

Notable strengths in the deployment preparation, if any.

### Validation gaps

Checks that could not be performed and the reason.

---

## Review independence

The reviewer must:

* inspect the actual configuration rather than trust the implementation summary
* avoid rewriting configuration unless explicitly requested
* avoid reducing severity to protect the implementation
* avoid increasing severity to make the review appear more rigorous
* distinguish confirmed defects from optional improvements
* report missing evidence as a validation gap
* never approve hosted-infrastructure creation on behalf of the user

## Completion criteria

This workflow is complete when:

* the complete change has been inspected
* every created or modified deployment file has been reviewed
* findings have supporting evidence
* findings have been classified by severity
* an overall assessment has been produced
* validation gaps have been documented

## Handoff rules

### Ready

Continue to:

* `.ai/workflows/validate-deployment.workflow.md`

### Ready with non-blocking suggestions

Continue to release validation.

Suggestions may be deferred when they do not affect:

* secret or credential exposure
* deployment topology integrity
* production pricing integrity
* evaluator local startup

### Not ready

Return the implementation to:

* `.ai/workflows/implement-deployment.workflow.md`

Provide the blocking and important findings as implementation inputs.

After correction, execute this review workflow again.

## Stop conditions

Stop the review and report insufficient evidence when:

* the changed or created files are unavailable
* the implementation report is unavailable and the deployment scope cannot be inferred
* hosted-provider configuration cannot be inspected
* the reviewer cannot distinguish the current change from unrelated repository changes

Do not approve a change when the available evidence is insufficient.
