import pytest

from app.config.settings import Settings
from app.integrations.llm.factory import get_llm_client
from app.integrations.llm.openai_client import OpenAIChatClient


def test_factory_returns_openai_client_for_openai_provider():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test")
    client = get_llm_client(settings)
    assert isinstance(client, OpenAIChatClient)


def test_factory_rejects_unknown_provider():
    settings = Settings(llm_provider="not_a_real_provider")
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        get_llm_client(settings)
