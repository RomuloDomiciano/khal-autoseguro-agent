from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM provider — never hardcode model or key.
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    llm_timeout_seconds: float = 20.0
    llm_max_retries: int = 1

    # Quote-service integration.
    quote_service_base_url: str = "http://localhost:8000"
    quote_service_connect_timeout_seconds: float = 3.0
    quote_service_read_timeout_seconds: float = 15.0
    quote_service_max_attempts: int = 3
    quote_service_backoff_base_seconds: float = 0.5
    quote_service_backoff_multiplier: float = 2.0
    quote_service_backoff_max_seconds: float = 4.0
    quote_service_backoff_jitter: float = 0.2

    # Agent behavior bounds.
    max_field_attempts: int = 2
    max_tool_iterations: int = 4

    # Observability.
    log_level: str = "INFO"

    # CORS — the frontend runs on a different origin (Vite dev server) than
    # this API, so the browser requires an explicit allow-list. Comma-separated.
    cors_allow_origins: str = "http://localhost:5173"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
