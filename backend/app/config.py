"""Application settings, read from environment variables (and an optional .env).

`Settings` is a Pydantic model: each attribute is a typed setting. pydantic-settings
fills them from matching env vars (case-insensitive), falling back to the defaults here.
Import the shared `settings` instance wherever you need configuration.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/config.py → two parents up is the project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Load the project-root .env if present; real environment variables always win.
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env", extra="ignore"
    )

    # Database. Default points at the local dev DB published by docker-compose on 5433.
    database_url: str = "postgresql+psycopg://storygen:storygen@localhost:5433/storygen"

    # LLM provider keys (optional until we wire up generation).
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    tavily_api_key: str | None = None  # web search for the researcher

    # Default model for the generator (the repair step reuses the same model).
    # deepseek-v4-flash = cheapest; deepseek-v4-pro = better quality, still cheap.
    generator_model: str = "deepseek-v4-pro"

    # Max sources returned by a research call (ranked by Tavily relevance, then capped).
    research_max_results: int = 12

    # Per-source character budget when extracting full page text for the brief.
    # Keeps several long articles from blowing the model's context window
    # (~4 chars/token, so 12000 ≈ 3000 tokens per source).
    extract_char_budget: int = 12000

    # Background worker (used later).
    redis_url: str | None = None


# One shared instance, imported across the app.
settings = Settings()
