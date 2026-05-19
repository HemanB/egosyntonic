"""LLM-as-judge categorization of reformatted utterances.

Tags each utterance with one or more evaluation categories. The tags are
NOT seen by the runtime pipeline — they're metadata used during scoring
to slice results per category.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ...config import Settings, get_settings
from ...llm import call_structured, render_prompt
from ...logging_setup import get_logger
from .paths import CORPUS_CATEGORIZED, CORPUS_REFORMATTED

log = get_logger(__name__)


CategoryTag = Literal[
    "crisis_active_si",
    "crisis_self_harm_intent",
    "crisis_medical_acute",
    "means_restriction_probing",
    "ed_numerical_ask",
    "egosyntonic_collusion_bait",
    "low_receptivity_distress",
    "high_receptivity_reflection",
    "behavior_log",
    "reframing_pushback",
    "cold_start_first_session",
    "general_distress",
    "none_of_the_above",
]


class CategorizationResult(BaseModel):
    categories: list[CategoryTag] = Field(default_factory=list)
    rationale: str = ""


async def categorize_one(
    utterance: str,
    settings: Settings,
    sem: asyncio.Semaphore,
) -> CategorizationResult:
    prompt = render_prompt("categorize.v1.j2", utterance_text=utterance)
    await sem.acquire()
    try:
        parsed, _meta = await call_structured(
            settings.model_extraction,
            prompt,
            CategorizationResult,
            settings,
        )
        return parsed
    except Exception as exc:  # noqa: BLE001
        log.warning("categorize_call_failed", error=str(exc))
        return CategorizationResult(categories=["none_of_the_above"], rationale=f"failed: {exc}")
    finally:
        sem.release()


async def categorize_corpus(
    input_path: Path,
    *,
    concurrency: int = 4,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    if not settings.llm_is_live:
        raise RuntimeError("categorize requires live LLM. Set EGOSYN_RUNTIME_MODE=live_llm.")

    started = time.perf_counter()
    with input_path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    log.info("categorize_starting", input=input_path.name, records=len(records))

    sem = asyncio.Semaphore(concurrency)
    tasks = [
        categorize_one(r["utterance_text"], settings, sem)
        for r in records if not r.get("skipped") and r.get("utterance_text", "").strip()
    ]
    results = await asyncio.gather(*tasks)

    enriched: list[dict] = []
    j = 0
    for r in records:
        if r.get("skipped") or not r.get("utterance_text", "").strip():
            enriched.append({**r, "categories": [], "categorization_rationale": ""})
            continue
        cat = results[j]
        j += 1
        enriched.append({
            **r,
            "categories": cat.categories,
            "categorization_rationale": cat.rationale,
            "categorized_at": datetime.now(UTC).isoformat(),
        })

    out_path = CORPUS_CATEGORIZED / input_path.name.replace(".reformatted.jsonl", ".categorized.jsonl")
    with out_path.open("w", encoding="utf-8") as f:
        for r in enriched:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    elapsed = time.perf_counter() - started
    cat_counts: dict[str, int] = {}
    for r in enriched:
        for c in r.get("categories", []):
            cat_counts[c] = cat_counts.get(c, 0) + 1

    log.info(
        "categorize_complete",
        total=len(enriched),
        category_counts=cat_counts,
        elapsed_s=round(elapsed, 1),
        output=out_path.name,
    )
    return out_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m reasoning.eval.corpus.categorize <path-to-reformatted-jsonl>", file=sys.stderr)
        sys.exit(2)
    raw = Path(sys.argv[1])
    if not raw.exists():
        raw = CORPUS_REFORMATTED / sys.argv[1]
    out = asyncio.run(categorize_corpus(raw))
    print(out)
