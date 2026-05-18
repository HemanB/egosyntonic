"""Multi-head retrieval over the user's longitudinal memory (idea.md §4.3).

Each reasoning head can issue its own queries. Live mode hits Vertex AI Vector
Search with metadata filters; fixture mode returns empty results.
"""

from __future__ import annotations

import asyncio

from ..config import Settings
from .types import ExtractionResult, RetrievalBundle, TurnInput


async def retrieve_for_all_heads(
    turn: TurnInput,
    extraction: ExtractionResult,
    settings: Settings,
) -> RetrievalBundle:
    if settings.is_fixture:
        return RetrievalBundle(items_by_head={
            "receptivity": [],
            "dynamical": [],
            "network": [],
            "sdt": [],
        })

    # Live retrieval fans out per head (idea.md §4.3 example query patterns)
    # TODO(Track B-live): wire Vertex AI Vector Search client + per-head query builders
    results = await asyncio.gather(
        _retrieve_receptivity(turn, extraction, settings),
        _retrieve_dynamical(turn, extraction, settings),
        _retrieve_network(turn, extraction, settings),
        _retrieve_sdt(turn, extraction, settings),
    )
    return RetrievalBundle(items_by_head={
        "receptivity": results[0],
        "dynamical": results[1],
        "network": results[2],
        "sdt": results[3],
    })


async def _retrieve_receptivity(turn: TurnInput, extraction: ExtractionResult, settings: Settings):  # noqa: ARG001
    raise NotImplementedError


async def _retrieve_dynamical(turn: TurnInput, extraction: ExtractionResult, settings: Settings):  # noqa: ARG001
    raise NotImplementedError


async def _retrieve_network(turn: TurnInput, extraction: ExtractionResult, settings: Settings):  # noqa: ARG001
    raise NotImplementedError


async def _retrieve_sdt(turn: TurnInput, extraction: ExtractionResult, settings: Settings):  # noqa: ARG001
    raise NotImplementedError
