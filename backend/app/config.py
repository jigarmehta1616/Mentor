"""Application settings, loaded from environment / .env. Never hardcode secrets."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["mock", "anthropic", "openai"]
ExplainLevel = Literal["eli5", "student", "expert"]


class Settings(BaseSettings):
    """Typed settings sourced from the environment (see .env.example)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: Provider = "mock"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    database_url: str = "postgresql://postgres:postgres@localhost:5432/mentor"

    # W: number of turns kept verbatim before older turns fold into the summary.
    context_window_turns: int = 8
    resource_cache_ttl_seconds: int = 86400
    port: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide singleton of settings. O(1) after first call."""
    return Settings()
