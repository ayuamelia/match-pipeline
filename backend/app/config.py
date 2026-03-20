# backend/app/config.py

from functools import lru_cache
from typing import Literal, Union
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────
    app_name: str = "Pelgo Match Pipeline"
    app_version: str = "1.0.0"
    environment: Literal["development",
                         "staging", "production"] = "development"
    secret_key: str = Field(..., min_length=32)

    # ── Database ───────────────────────────────────────────
    database_url: str = Field(
        ..., description="Must use asyncpg driver: postgresql+asyncpg://..."
    )

    @computed_field
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )

    db_pool_size: int = Field(default=10, ge=1, le=50)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_recycle: int = 1800

    # ── Redis / Celery ─────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_result_expires: int = 86400

    # ── Candidate ─────────────────────────────────────────
    candidate_id: str = Field(
        ..., description="UUID of the seeded candidate."
    )

    # ── Rate limiting ──────────────────────────────────────
    api_rate_limit: str = "20/minute"

    # ── OpenAI (optional) ─────────────────────────────────
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout: int = 30

    @computed_field
    @property
    def use_llm_scoring(self) -> bool:
        return bool(self.openai_api_key)

    # ── Worker ─────────────────────────────────────────────
    worker_max_retries: int = 3
    worker_retry_backoff_base: int = 60
    worker_task_timeout: int = 120

    # ── CORS ───────────────────────────────────────────────
    cors_origins: Union[list[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str] | object:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Pagination ─────────────────────────────────────────
    default_page_limit: int = 20
    max_page_limit: int = 100


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
