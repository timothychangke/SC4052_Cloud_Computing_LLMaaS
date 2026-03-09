"""
Centralised config. Reads from environment / .env file so we never
hard-code secrets or connection strings in application code.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # -- Postgres --
    database_dsn: str = "postgresql://postgres:postgres@localhost:5432/adllm"

    # -- Redis --
    redis_url: str = "redis://localhost:6379/0"

    # -- App --
    base_url: str = "http://localhost:8000"
    session_ttl_seconds: int = 1800  # 30 min inactivity
    max_history_turns: int = 10

    # -- AI module mode: "mock" while teammate is still building, "real" for prod --
    ai_module_mode: str = "mock"
    
    # -- Groq secret key --
    groq_api_key: str = ""

    # -- CORS --
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
