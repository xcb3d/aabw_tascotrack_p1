from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://mytasco:mytasco@localhost:5432/mytasco"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    OPENAI_API_KEY: str = ""
    APP_CODE: str = "MYTASCO"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide settings singleton."""
    return Settings()
