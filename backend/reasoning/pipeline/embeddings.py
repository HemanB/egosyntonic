"""Utterance embeddings via Gemini API.

Uses `gemini-embedding-001` with Matryoshka truncation to 768 dims to match
the Firestore vector index built in `infra/firestore.tf` and the
`EGOSYN_UTTERANCES_COLLECTION` config.

In fixture / live_llm modes this returns a zero vector — retrieval is
mocked anyway and the embedding isn't used. Only full live mode produces
real embeddings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import Settings
from ..logging_setup import get_logger

if TYPE_CHECKING:
    pass

log = get_logger(__name__)

EMBEDDING_DIM = 768
EMBEDDING_MODEL = "gemini-embedding-001"


async def embed_text(text: str, settings: Settings) -> list[float]:
    """Return a 768-dim embedding vector for the given text.

    In fixture / live_llm mode returns a zero vector — retrieval is mocked
    and the embedding isn't actually used. Live mode calls the Gemini
    Embedding API.
    """
    if not settings.storage_is_live:
        return [0.0] * EMBEDDING_DIM

    from ..llm import _get_client  # noqa: PLC0415  (reuse the genai client)

    client = _get_client(settings)
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={
            "task_type": "SEMANTIC_SIMILARITY",
            "output_dimensionality": EMBEDDING_DIM,
        },
    )
    # The response shape varies slightly across SDK versions; both .embeddings
    # (list) and .embedding (single) have been seen. Tolerate both.
    embeddings_attr = getattr(response, "embeddings", None)
    if embeddings_attr:
        vec = embeddings_attr[0]
        values = getattr(vec, "values", None) or vec
    else:
        emb = getattr(response, "embedding", None)
        if emb is None:
            raise RuntimeError(f"unexpected embed_content response shape: {type(response).__name__}")
        values = getattr(emb, "values", None) or emb

    if len(values) != EMBEDDING_DIM:
        log.warning(
            "embedding_dim_mismatch",
            expected=EMBEDDING_DIM,
            got=len(values),
        )
    return list(values)
