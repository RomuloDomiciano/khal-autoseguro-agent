"""Top-level exception handling — the concrete mechanism behind "the agent
must never crash." Any unhandled exception anywhere in the request lifecycle
is caught here, logged with full detail server-side, and turned into a safe,
generic response with no stack trace or internal detail exposed to the lead.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.observability.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "error.unhandled",
            path=request.url.path,
            method=request.method,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Algo deu errado do nosso lado. Um atendente vai continuar essa conversa.",
            },
        )
