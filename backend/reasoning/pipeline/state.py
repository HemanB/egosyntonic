"""Per-user state document read/write (idea.md §3.5).

Backed by Firestore in live mode; in-memory dict in fixture mode for tests.
State updates run asynchronously after the user-visible response is delivered
so they don't count against the latency budget.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..config import Settings


_FIXTURE_STORE: dict[str, dict[str, Any]] = {}


async def read_state(user_id: str, settings: Settings) -> dict[str, Any]:
    if settings.is_fixture:
        return _FIXTURE_STORE.setdefault(user_id, _empty_state(user_id))
    # TODO(Track B-live): wire google-cloud-firestore read
    raise NotImplementedError("live-mode state read not yet implemented")


async def update_state(
    user_id: str,
    patch: dict[str, Any],
    settings: Settings,
) -> None:
    if settings.is_fixture:
        current = _FIXTURE_STORE.setdefault(user_id, _empty_state(user_id))
        current.update(patch)
        current["updated_at"] = datetime.now(UTC).isoformat()
        return
    # TODO(Track B-live): wire google-cloud-firestore write + audit log entry
    raise NotImplementedError("live-mode state update not yet implemented")


def _empty_state(user_id: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "schema_version": "1.0.0",
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "intake_completed_at": None,
        "condition_pack": "eating_disorder",
        "stated_chief_complaint": {"text": "", "stated_at": now, "edit_history": []},
        "network_state": {
            "nodes": [],
            "edges": [],
            "last_updated": now,
            "data_density": {"utterance_count": 0, "weeks_of_use": 0.0},
        },
        "need_state_model": {},
        "receptivity_history": [],
        "active_loops": [],
        "insight_surface_state": {"surfaced_insights": []},
        "safety_state": {"active_flags": [], "crisis_history": []},
        "user_preferences": {"insight_intensity": "moderate", "tracking_enabled": True},
    }
