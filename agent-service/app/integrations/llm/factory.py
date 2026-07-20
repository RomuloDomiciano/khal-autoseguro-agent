from __future__ import annotations

from app.config.settings import Settings
from app.integrations.llm.base import LLMClient
from app.integrations.llm.openai_client import OpenAIChatClient


def get_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "openai":
        return OpenAIChatClient(settings)
    raise ValueError(
        f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}. "
        "Only 'openai' is implemented; add a new LLMClient implementation "
        "and a branch here to support another provider."
    )
