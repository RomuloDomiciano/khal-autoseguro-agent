# Implement deployment 

Act as the Deployment Engineer for the AutoSeguro repository.

Your task is to prepare the project for both:

1. Hosted deployment:
   - frontend on Vercel
   - agent-service and quote-service on Render or Railway

2. Local evaluator execution:
   - preferably through one Docker Compose command
   - with manual fallback instructions

Before making any change:

1. Inspect the complete repository.
2. Identify:
   - repository structure
   - frontend framework and build command
   - backend framework and startup commands
   - Python dependency manager
   - existing Dockerfiles
   - current docker-compose configuration
   - health endpoints
   - environment variables
   - CORS behavior
   - frontend API URL behavior
   - service-to-service URL configuration
   - timeout and retry configuration
3. Present a concise deployment plan.
4. Classify each required change as:
   - REQUIRED
   - RECOMMENDED
   - ALREADY READY
   - NEEDS USER ACTION

After presenting the plan, apply safe, local, and reversible changes.

Expected deployment topology:

Browser
  -> Vercel frontend
  -> agent-service
  -> quote-service

The browser must never call quote-service directly.
The OpenAI API key must only exist in agent-service.

Validate or create, only where needed:

- production-ready Dockerfile for agent-service
- production-ready Dockerfile for quote-service
- frontend deployment configuration
- complete docker-compose.yml
- .env.example files
- explicit health checks
- CORS configuration using environment variables
- service URLs using environment variables
- README deployment and local startup sections
- deployment readiness checklist

For Docker Compose, the desired evaluator experience is approximately:

cp agent-service/.env.example agent-service/.env
# add OPENAI_API_KEY
docker compose up --build

Do not assume commands. Use the actual project structure and dependency managers.

Hosted deployment targets:

Frontend:
- Vercel
- configure the production API URL through an environment variable

APIs:
- Render or Railway
- configure each service from its own root directory or Dockerfile
- use /health for health checks when available

Required validation:

1. Run all backend tests.
2. Run frontend tests.
3. Run frontend production build.
4. Build every Docker image.
5. Start the complete stack with Docker Compose.
6. Call all health endpoints.
7. Execute at least one successful end-to-end quote flow.
8. Execute one failure or handoff scenario.
9. Verify no secret is committed or exposed to the frontend.
10. Verify the production frontend does not use demo/mock pricing.

Do not:
- change business logic
- add MCP, RAG, vector databases, queues, Kubernetes, Terraform, or databases
- replace frameworks
- weaken tests
- fabricate successful validation
- deploy, push, or change git remotes without explicit approval

At the end, produce:

## Deployment Readiness Report

### Topology
### Files changed
### Environment variables
### Local startup
### Hosted deployment instructions
### Validation commands
### Validation results
### Remaining manual actions
### Known limitations
### Final status

Use one final status only:

READY_FOR_DEPLOYMENT
READY_WITH_LIMITATIONS
NOT_READY