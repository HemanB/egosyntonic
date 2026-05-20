"""Multi-head retrieval over the user's longitudinal memory (idea.md §4.3).

Each reasoning head can issue its own queries. Live mode hits Firestore's
`FindNearest` on the utterances collection with a `user_id` prefix filter;
fixture / live_llm modes return empty results. See ADR-0001 for the store
choice.

The per-head query patterns from idea.md §4.3:

- Receptivity head: prior turns in similar affective states, recency-weighted
- Dynamical head: prior instances of the currently-active loop; transitions
- Network head: prior co-activations of currently-active nodes
- SDT head: prior expressions of thwarting in implicated need-domains

v1 implements a single semantic FindNearest per head. Metadata-filtered
variants (e.g. recency weighting, behavior tags) are deferred — Firestore
vector queries can combine `.where()` filters with `find_nearest` but
each head needs its own filter logic. Tracked in #20.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ..config import Settings
from ..logging_setup import get_logger
from .types import ExtractionResult, RetrievalBundle, RetrievedItem, TurnInput

log = get_logger(__name__)


_PER_HEAD_LIMIT = 3  # top-K to surface per head


async def retrieve_for_all_heads(
    turn: TurnInput,
    extraction: ExtractionResult,
    settings: Settings,
    *,
    utterance_embedding: list[float] | None = None,
) -> RetrievalBundle:
    if not settings.storage_is_live:
        return RetrievalBundle(items_by_head={
            "receptivity": [],
            "dynamical": [],
            "network": [],
            "sdt": [],
        })

    if utterance_embedding is None:
        # Lazy embed if the caller didn't pre-compute one.
        from .embeddings import embed_text  # noqa: PLC0415

        utterance_embedding = await embed_text(turn.utterance_text, settings)

    # Fan out per-head queries. They're all FindNearest against the same
    # collection right now; metadata-filtered variants are deferred (#20).
    results = await asyncio.gather(
        _retrieve_one_head("receptivity", turn.user_id, utterance_embedding, settings),
        _retrieve_one_head("dynamical", turn.user_id, utterance_embedding, settings),
        _retrieve_one_head("network", turn.user_id, utterance_embedding, settings),
        _retrieve_one_head("sdt", turn.user_id, utterance_embedding, settings),
    )
    return RetrievalBundle(items_by_head={
        "receptivity": results[0],
        "dynamical": results[1],
        "network": results[2],
        "sdt": results[3],
    })


async def _retrieve_one_head(
    head: str,
    user_id: str,
    embedding: list[float],
    settings: Settings,
) -> list[RetrievedItem]:
    """Run a single FindNearest query for one head against the utterances
    collection, prefix-filtered by user_id."""
    from google.cloud.firestore_v1.base_query import FieldFilter  # noqa: PLC0415
    from google.cloud.firestore_v1.base_vector_query import DistanceMeasure  # noqa: PLC0415
    from google.cloud.firestore_v1.vector import Vector  # noqa: PLC0415

    from .firestore_client import get_client  # noqa: PLC0415

    db = get_client(settings)
    collection = db.collection(settings.utterances_collection)
    query = collection.where(filter=FieldFilter("user_id", "==", user_id)).find_nearest(
        vector_field="embedding",
        query_vector=Vector(embedding),
        limit=_PER_HEAD_LIMIT,
        distance_measure=DistanceMeasure.COSINE,
    )

    docs = await query.get()
    items: list[RetrievedItem] = []
    for d in docs:
        data = d.to_dict() or {}
        excerpt = data.get("text", "")[:400]
        occurred_at = data.get("extracted_at") or data.get("created_at") or datetime.now(UTC).isoformat()
        if isinstance(occurred_at, str):
            try:
                occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            except ValueError:
                occurred_at = datetime.now(UTC)
        items.append(RetrievedItem(
            ref_type="utterance",
            ref_id=d.id,
            excerpt=excerpt,
            occurred_at=occurred_at,
            score=0.5,  # Firestore doesn't return distance — we'd need pre-norm + recompute
            head_origin=head,  # type: ignore[arg-type]
        ))
    log.debug("retrieval_head_complete", head=head, user_id=user_id, hits=len(items))
    return items


async def write_utterance(
    user_id: str,
    turn: TurnInput,
    extraction: ExtractionResult,
    embedding: list[float],
    settings: Settings,
) -> str | None:
    """Persist an utterance record to Firestore (live mode only).

    Returns the document ID or None if storage isn't live. Called by the
    orchestrator after extraction; safe to fire-and-forget alongside the
    state update.
    """
    if not settings.storage_is_live:
        return None

    from google.cloud.firestore_v1.vector import Vector  # noqa: PLC0415

    from .firestore_client import get_client  # noqa: PLC0415

    db = get_client(settings)
    doc_id = extraction.utterance_id
    doc = {
        "user_id": user_id,
        "session_id": turn.session_id,
        "text": turn.utterance_text,
        "embedding": Vector(embedding),
        "extracted_at": extraction.extracted_at.isoformat(),
        "model_id": extraction.model_id,
        "prompt_template_version": extraction.prompt_template_version,
        # Extraction features inlined for metadata-filtered retrieval later
        "affective_valence": {
            "valence": extraction.affective_valence.valence,
            "arousal": extraction.affective_valence.arousal,
        },
        "behaviors_referenced": [
            {"behavior_id": b.behavior_id, "stance": b.stance}
            for b in extraction.behaviors_referenced
        ],
        "network_nodes_activated": [
            n.node_id for n in extraction.network_nodes_activated
        ],
        "implicated_need_states": [
            {"need": n.need, "domain": n.domain, "polarity": n.polarity}
            for n in extraction.implicated_need_states
        ],
        "low_information": extraction.low_information,
        "safety_signals_active": extraction.safety_signals.any_active,
    }
    await db.collection(settings.utterances_collection).document(doc_id).set(doc)
    log.debug("utterance_written", user_id=user_id, utterance_id=doc_id)
    return doc_id
