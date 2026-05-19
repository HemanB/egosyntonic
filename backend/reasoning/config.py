"""Application configuration, loaded once at startup from env vars."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(str, Enum):
    fixture = "fixture"            # everything deterministic, no external calls
    live_llm = "live_llm"          # real Gemini calls; retrieval + state stay in-memory
    live = "live"                  # full GCP integration (Firestore vector search + state)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Load .env first, then .env.local override.
        # pydantic-settings reads later files with higher precedence.
        env_file=(".env", ".env.local"),
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
    # Firestore-backed retrieval (ADR-0001). Collection holding utterance docs
    # with an `embedding` vector field; queried via FindNearest at runtime.
    utterances_collection: str = Field(default="utterances", alias="EGOSYN_UTTERANCES_COLLECTION")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    otel_enabled: bool = Field(default=False, alias="EGOSYN_OTEL_ENABLED")

    dev_auth_bypass: bool = Field(default=False, alias="EGOSYN_DEV_AUTH_BYPASS")
    dev_bypass_user_id: str = Field(default="local-dev-user", alias="EGOSYN_DEV_BYPASS_USER_ID")

    # Reddit — eval corpus only; never used in prod
    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(default=None, alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str | None = Field(default=None, alias="REDDIT_USER_AGENT")

    @property
    def is_fixture(self) -> bool:
        return self.runtime_mode == RuntimeMode.fixture

    @property
    def llm_is_live(self) -> bool:
        """True for both live_llm and live modes — i.e. real Gemini calls."""
        return self.runtime_mode in (RuntimeMode.live_llm, RuntimeMode.live)

    @property
    def storage_is_live(self) -> bool:
        """True only for full live mode — Firestore (state + vector retrieval)."""
        return self.runtime_mode == RuntimeMode.live


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
