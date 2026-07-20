from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.orchestrator import ConversationOrchestrator
from app.api.routes.conversations import router as conversations_router
from app.config.settings import get_settings
from app.domain.repository import InMemoryConversationRepository
from app.integrations.llm.factory import get_llm_client
from app.integrations.quote_service.client import HttpxQuoteServiceClient
from app.observability.errors import register_exception_handlers
from app.observability.logging import configure_logging, get_logger
from app.observability.middleware import CorrelationIdMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    quote_client = HttpxQuoteServiceClient(settings)
    llm_client = get_llm_client(settings)
    repository = InMemoryConversationRepository()

    plans_catalog: list[dict] = []
    try:
        plans = await quote_client.get_plans()
        plans_catalog = plans.get("planos", [])
    except Exception as exc:  # noqa: BLE001 — best-effort only, must not block startup
        logger.warning("startup.plans_fetch_failed", exc_info=exc)

    app.state.orchestrator = ConversationOrchestrator(
        llm_client=llm_client,
        quote_client=quote_client,
        repository=repository,
        settings=settings,
        plans_catalog=plans_catalog,
    )
    yield


app = FastAPI(title="AutoSeguro Agent Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(CorrelationIdMiddleware)
register_exception_handlers(app)
app.include_router(conversations_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
