"""Async Firestore client — lazy, shared across pipeline stages.

One client per process. Initialized on first call to `get_client()`. Backed
by Application Default Credentials in local dev (via `gcloud auth
application-default login`) and by the Cloud Run service identity in
deployed contexts.

In fixture and live_llm modes this module is not imported. Only
`settings.storage_is_live` (full live mode) triggers Firestore use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import Settings
from ..logging_setup import get_logger

if TYPE_CHECKING:
    from google.cloud.firestore_v1 import AsyncClient

log = get_logger(__name__)

_client: "AsyncClient | None" = None


def get_client(settings: Settings) -> "AsyncClient":
    """Return the singleton AsyncClient. Lazily initializes."""
    global _client
    if _client is not None:
        return _client

    from google.cloud.firestore_v1 import AsyncClient  # noqa: PLC0415

    if not settings.google_cloud_project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT must be set for live-mode Firestore use."
        )
    _client = AsyncClient(project=settings.google_cloud_project)
    log.info("firestore_client_initialized", project=settings.google_cloud_project)
    return _client


def reset_client_for_tests() -> None:
    """Wipe the singleton — test-only helper."""
    global _client
    _client = None
