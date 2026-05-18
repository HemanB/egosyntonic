"""Application configuration, loaded once at startup from env vars."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(str, Enum):
    fixture = "fixture"
    live = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    runtime_mode: RuntimeMode = Field(default=RuntimeMode.fixture, alias="EGOSYN_RUNTIME_MODE")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    model_reasoning: str = Field(default="gemini-2.5-pro", alias="EGOSYN_MODEL_REASONING")
    model_critic: str = Field(default="gemini-2.5-pro", alias="EGOSYN_MODEL_CRITIC")
    model_extraction: str = Field(default="gemini-2.5-flash", alias="EGOSYN_MODEL_EXTRACTION")
    model_generation: str = Field(default="gemini-2.5-flash", alias="EGOSYN_MODEL_GENERATION")

    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    firebase_project_id: str | None = Field(default=None, alias="FIREBASE_PROJECT_ID")
    vertex_vector_index_endpoint: str | None = Field(default=None, alias="VERTEX_VECTOR_INDEX_ENDPOINT")
    vertex_vector_index_id: str | None = Field(default=None, alias="VERTEX_VECTOR_INDEX_ID")
    vertex_region: str = Field(default="us-central1", alias="VERTEX_REGION")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    otel_enabled: bool = Field(default=False, alias="EGOSYN_OTEL_ENABLED")

    dev_auth_bypass: bool = Field(default=False, alias="EGOSYN_DEV_AUTH_BYPASS")
    dev_bypass_user_id: str = Field(default="local-dev-user", alias="EGOSYN_DEV_BYPASS_USER_ID")

    @property
    def is_fixture(self) -> bool:
        return self.runtime_mode == RuntimeMode.fixture


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
