"""Per-user state document read/write (idea.md §3.5).

Backed by Firestore in full live mode; in-memory dict in fixture and
live_llm modes (live_llm tests CoT quality without GCP storage). State
updates run asynchronously after the user-visible response is delivered.

Firestore layout:
- `users/{user_id}` — state document (one per user)
- `users/{user_id}/audit/{auto_id}` — append-only audit log entries
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ..config import Settings
from ..logging_setup import get_logger

log = get_logger(__name__)


_FIXTURE_STORE: dict[str, dict[str, Any]] = {}


async def read_state(user_id: str, settings: Settings) -> dict[str, Any]:
    if not settings.storage_is_live:
        return _FIXTURE_STORE.setdefault(user_id, _empty_state(user_id))

    from .firestore_client import get_client  # noqa: PLC0415

    db = get_client(settings)
    doc_ref = db.collection("users").document(user_id)
    snap = await doc_ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        await _audit(user_id, op="read", fields_touched=list(data.keys()), settings=settings)
        return data

    # First touch: create + return the empty state.
    empty = _empty_state(user_id)
    await doc_ref.set(empty)
    await _audit(user_id, op="create", fields_touched=list(empty.keys()), settings=settings)
    log.info("state_created", user_id=user_id)
    return empty


async def update_state(
    user_id: str,
    patch: dict[str, Any],
    settings: Settings,
) -> None:
    if not settings.storage_is_live:
        current = _FIXTURE_STORE.setdefault(user_id, _empty_state(user_id))
        current.update(patch)
        current["updated_at"] = datetime.now(UTC).isoformat()
        return

    from .firestore_client import get_client  # noqa: PLC0415

    patch_to_apply = dict(patch)
    patch_to_apply["updated_at"] = datetime.now(UTC).isoformat()

    db = get_client(settings)
    doc_ref = db.collection("users").document(user_id)
    # Merge=True means only the fields in `patch` get overwritten; existing
    # fields not in the patch are preserved.
    await doc_ref.set(patch_to_apply, merge=True)
    await _audit(
        user_id,
        op="update",
        fields_touched=list(patch.keys()),
        settings=settings,
    )


async def _audit(
    user_id: str,
    *,
    op: str,
    fields_touched: list[str],
    settings: Settings,
    turn_id: str | None = None,
) -> None:
    """Write an append-only audit log entry."""
    from .firestore_client import get_client  # noqa: PLC0415

    db = get_client(settings)
    audit_id = uuid.uuid4().hex
    entry = {
        "op": op,
        "fields_touched": fields_touched,
        "turn_id": turn_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    await db.collection("users").document(user_id).collection("audit").document(audit_id).set(entry)


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
