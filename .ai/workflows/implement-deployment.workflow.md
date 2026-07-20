# Deployment Preparation Workflow

Use this workflow to prepare the repository for local and hosted deployment.

## Purpose

Coordinate the deployment-preparation process using the deployment engineering agent and the implementation prompt.

This workflow defines the execution sequence. Detailed implementation rules are defined in the referenced agent and prompt files.

## Required inputs

Before starting, ensure the following information is available:

* target hosting providers, if already decided (default: Vercel for frontend, Render or Railway for backend services)
* whether hosted deployment is in scope for this pass, or only local Docker Compose readiness
* any existing deployment documentation or prior deployment attempts
* known constraints (free-tier limits, cold starts, required custom domains)

Do not invent missing infrastructure requirements. When hosted deployment decisions are not explicit, prepare the configuration but do not create hosted resources without approval.

## Context

Use:

* `.ai/agents/deployment-engineer.yaml`
* `.ai/prompts/implement-deploy.md`
* `.ai/project/context.md`

Read only the source files necessary to understand the current deployment posture:

* repository root
* `frontend/`
* `agent-service/`
* `quote-service/`
* existing Dockerfiles
* existing `docker-compose.yml`
* `.env.example` files
* README files
* health endpoints
* test configuration
* build configuration

## Expected deployment topology

```text
Browser
  |
  v
Frontend
  |
  v
Agent Service
  |
  v
Quote Service

Agent Service
  |
  v
OpenAI API
```

Rules:

* the browser must call only the agent-service
* the browser must not call the quote-service directly
* the OpenAI API key must exist only in the agent-service environment
* the quote-service remains the only source of truth for prices
* production configuration must not use demo or mock pricing

## Execution

### Step 1 — Inspect the repository

Inspect the repository before changing files.

Identify:

* frontend framework
* frontend package manager
* frontend build command
* frontend test command
* frontend production output
* agent-service framework
* quote-service framework
* Python dependency manager
* backend startup commands
* backend test commands
* existing Docker configuration
* health endpoints
* environment variables
* current CORS behavior
* frontend API URL configuration
* agent-to-quote-service URL configuration
* retry and timeout configuration

Do not assume commands based only on convention. Use the actual repository configuration.

### Step 2 — Define the deployment readiness plan

Before making changes, produce a concise plan.

Classify every relevant item as:

* `ALREADY_READY`
* `REQUIRED`
* `RECOMMENDED`
* `NEEDS_USER_ACTION`
* `NOT_APPLICABLE`

Include:

* files that may need modification
* files that may need creation
* validation commands
* external actions that require user approval

Safe, local, and reversible changes may proceed after the plan is presented.

Stop and request approval before:

* changing Git remotes
* committing or pushing
* creating hosted services
* configuring billing
* adding custom domains
* storing production secrets
* deleting intentionally retained features
* making incompatible API changes

### Step 3 — Prepare local deployment

Execute the instructions in:

* `.ai/prompts/implement-deploy.md`

Validate or create, only when needed:

* production Dockerfile for agent-service
* production Dockerfile for quote-service
* complete root `docker-compose.yml`
* `.dockerignore` files
* `.env.example` files
* health checks
* service startup commands
* network configuration
* frontend API URL injection
* agent-service to quote-service connectivity

The desired evaluator experience is:

```bash
cp agent-service/.env.example agent-service/.env
# Add OPENAI_API_KEY to agent-service/.env

docker compose up --build
```

The exact commands and file paths must reflect the repository.

The complete local stack should expose, when applicable: frontend, agent-service, agent-service API documentation, quote-service, and health endpoints.

### Step 4 — Prepare hosted deployment configuration

Prepare instructions for:

**Frontend** — preferred target: Vercel. Validate root directory, install command, build command, output directory, production API environment variable, SPA routing behavior if applicable, and CORS compatibility with the backend.

**Agent Service** — preferred target: Render or Railway. Validate service root, Dockerfile or native build, start command, health-check path, required environment variables, OpenAI secret handling, quote-service URL, allowed frontend origins, and timeout configuration.

**Quote Service** — preferred target: Render or Railway. Validate service root, Dockerfile or native build, start command, health-check path, required environment variables, and network accessibility from agent-service.

Do not perform hosted deployment without explicit approval.

### Step 5 — Review runtime configuration

Verify:

* secrets are not committed
* `.env` files are ignored
* `.env.example` contains placeholders only
* OpenAI credentials never enter frontend code or bundles
* frontend production URL is environment-driven
* quote-service URL is environment-driven
* CORS origins are environment-driven
* localhost defaults are safe for development
* production defaults do not silently point to localhost
* timeout values support the known quote-service latency
* retry behavior is preserved

Do not print actual secret values.

### Step 6 — Run implementation validation

Run all applicable validations, covering at minimum:

* backend: agent-service tests, quote-service tests, static checks if configured, import/startup validation
* frontend: tests, lint if configured, type checking if configured, production build
* containers: build every Docker image, start the complete stack, inspect container status, call every health endpoint, verify service-to-service connectivity

End-to-end, execute at least:

* one successful quote flow
* one invalid or ineligible vehicle flow
* one failure, retry, or human-handoff flow
* one multi-message correction flow

Verify:

* the frontend communicates with the real backend
* pricing comes only from quote-service
* no mock pricing is used in production
* the agent does not fabricate prices
* health endpoints return success
* logs do not expose secrets

If a validation cannot be executed, report it honestly as `NOT_EXECUTED` with the reason. Never fabricate successful results.

### Step 7 — Update documentation

Update the root README only where needed. It should include:

* architecture overview
* production demo URL placeholders
* quick start with Docker Compose
* manual local setup
* required environment variables
* service ports
* health endpoints
* API documentation URL
* test commands
* deployment instructions
* evaluator walkthrough
* cold-start note, if using free-tier hosting
* known limitations

Recommended evaluator walkthrough: start or open the application, begin a quote conversation, provide information across multiple messages, complete a successful quote, test a user correction, test an invalid or unsupported scenario, then inspect API documentation and health endpoints.

### Step 8 — Produce the implementation report

Return:

## Deployment Readiness Report

### Summary

### Deployment Topology

### Existing Configuration

### Files Created

### Files Changed

### Environment Variables

### Local Startup Instructions

### Hosted Deployment Instructions

### Validation Commands and Results

Use a table with:

| Validation | Status | Evidence |
| --- | --- | --- |

Allowed statuses:

* `PASSED`
* `FAILED`
* `NOT_EXECUTED`
* `NOT_APPLICABLE`

### Remaining Manual Actions

### Known Limitations

### Risks

### Final Status

Use exactly one:

* `READY_FOR_DEPLOYMENT`
* `READY_WITH_LIMITATIONS`
* `NOT_READY`

The implementation report becomes the input for the review workflow.

## Constraints

Do not:

* change business rules
* redesign the conversational architecture
* introduce multiple product agents without need
* add MCP, RAG, embeddings, or vector databases
* add Kubernetes, Terraform, or queues
* add databases
* replace frameworks
* weaken tests
* hide failures
* commit or push
* create hosted infrastructure without approval

## Completion criteria

This workflow is complete when:

* the repository has been inspected and the deployment plan presented
* safe, local, and reversible changes have been applied
* local Docker Compose startup has been validated
* hosted deployment configuration has been prepared, pending approval to provision
* runtime configuration has been reviewed for secret exposure
* applicable validations have been executed and recorded
* documentation has been updated where needed
* an implementation report with a final status has been produced

## Handoff rules

### READY_FOR_DEPLOYMENT / READY_WITH_LIMITATIONS

Continue to:

* `.ai/workflows/review-deployment.workflow.md`

### NOT_READY

Resolve the blocking items identified in the implementation report and repeat this workflow before requesting review.