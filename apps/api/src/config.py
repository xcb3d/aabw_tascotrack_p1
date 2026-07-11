from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://mytasco:mytasco@localhost:5432/mytasco"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production-32-bytes-minimum"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "mytasco"
    JWT_AUDIENCE: str = "mytasco-ai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-sol"
    OPENAI_BASE_URL: str = ""
    OPENAI_TIMEOUT_SECONDS: float = 45.0
    OPENAI_ZDR_VERIFIED: bool = False
    OPENAI_ENABLED: bool = False
    MOCK_ADAPTERS_ENABLED: bool = True
    INTERNAL_EMBEDDINGS_ENABLED: bool = False
    CONFIRMATION_SIGNING_KEY: str = "change-me-confirmation-key"
    CONFIRMATION_TTL_SECONDS: int = 300
    RUN_DEADLINE_SECONDS: int = 90
    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024
    DEFAULT_TENANT_ID: str = "demo-mytasco"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OBJECT_STORAGE_BACKEND: str = "local"
    OBJECT_STORAGE_LOCAL_ROOT: str = "tmp/object_store"
    OBJECT_STORAGE_BUCKET: str = ""
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_REGION: str = ""
    APP_CODE: str = "MYTASCO"

    def production_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.ENV.lower() == "production":
            if len(self.JWT_SECRET.encode()) < 32:
                errors.append("JWT_SECRET must contain at least 32 bytes")
            if self.JWT_SECRET == "change-me-in-production-32-bytes-minimum":
                errors.append("JWT_SECRET must be configured")
            if self.CONFIRMATION_SIGNING_KEY == "change-me-confirmation-key":
                errors.append("CONFIRMATION_SIGNING_KEY must be configured")
            if self.MOCK_ADAPTERS_ENABLED:
                errors.append("MOCK_ADAPTERS_ENABLED must be false")
            if not self.INTERNAL_EMBEDDINGS_ENABLED:
                errors.append("INTERNAL_EMBEDDINGS_ENABLED must be true")
            if self.OBJECT_STORAGE_BACKEND != "s3" or not self.OBJECT_STORAGE_BUCKET:
                errors.append("production requires an S3-compatible OBJECT_STORAGE_BUCKET")
        if self.OPENAI_ENABLED and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when OPENAI_ENABLED=true")
        if self.OPENAI_ENABLED and not self.OPENAI_ZDR_VERIFIED:
            errors.append("OPENAI_ZDR_VERIFIED must be true before hosted generation is enabled")
        return tuple(errors)


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide settings singleton."""
    return Settings()
