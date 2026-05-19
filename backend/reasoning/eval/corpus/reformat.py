"""Reformat anonymized Reddit posts into conversational journaling utterances.

Runs after fetch + anonymize, before the pipeline eval. Output: JSONL of
ReformattedUtterance records ready to feed through /turn.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...config import Settings, get_settings
from ...llm import call_text, render_prompt
from ...logging_setup import get_logger
from .anonymize import anonymize_record
from .paths import CORPUS_DATA, CORPUS_REFORMATTED

log = get_logger(__name__)


SKIP_TOKEN = "SKIP"


@dataclass(slots=True)
class ReformattedUtterance:
    id_hash: str
    subreddit: str
    utterance_text: str
    reformat_model: str
    reformat_template_version: str
    skipped: bool = False
    skip_reason: str | None = None
    raw_chars: int = 0
    reformatted_chars: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


async def reformat_one(
    record: dict[str, Any],
    settings: Settings,
    *,
    concurrency_token: asyncio.Semaphore | None = None,
) -> ReformattedUtterance:
    anonymized = anonymize_record(record)
    body = anonymized["body"]

    prompt = render_prompt("reformat.v1.j2", post_body=body)

    if concurrency_token is not None:
        await concurrency_token.acquire()
    try:
        text, meta = await call_text(settings.model_extraction, prompt, settings)
    except Exception as exc:  # noqa: BLE001
        log.warning("reformat_call_failed", id_hash=anonymized["id_hash"], error=str(exc))
        return ReformattedUtterance(
            id_hash=anonymized["id_hash"],
            subreddit=anonymized["subreddit"],
            utterance_text="",
            reformat_model=settings.model_extraction,
            reformat_template_version="1.0.0",
            skipped=True,
            skip_reason=f"call_failed: {exc}",
            raw_chars=len(body),
        )
    finally:
        if concurrency_token is not None:
            concurrency_token.release()

    stripped = text.strip()
    if not stripped:
        return ReformattedUtterance(
            id_hash=anonymized["id_hash"],
            subreddit=anonymized["subreddit"],
            utterance_text="",
            reformat_model=meta.model_id,
            reformat_template_version=meta.prompt_template_version,
            skipped=True,
            skip_reason="empty_response_likely_safety_filter",
            raw_chars=len(body),
        )
    if stripped.upper() == SKIP_TOKEN or stripped.startswith(f"{SKIP_TOKEN}\n"):
        return ReformattedUtterance(
            id_hash=anonymized["id_hash"],
            subreddit=anonymized["subreddit"],
            utterance_text="",
            reformat_model=meta.model_id,
            reformat_template_version=meta.prompt_template_version,
            skipped=True,
            skip_reason="model_skipped_unsuitable_content",
            raw_chars=len(body),
        )

    return ReformattedUtterance(
        id_hash=anonymized["id_hash"],
        subreddit=anonymized["subreddit"],
        utterance_text=stripped,
        reformat_model=meta.model_id,
        reformat_template_version=meta.prompt_template_version,
        raw_chars=len(body),
        reformatted_chars=len(stripped),
    )


async def reformat_corpus(
    input_path: Path,
    *,
    concurrency: int = 4,
    settings: Settings | None = None,
    output_filename: str | None = None,
) -> Path:
    settings = settings or get_settings()
    if not settings.llm_is_live:
        raise RuntimeError(
            "reformat requires live LLM. Set EGOSYN_RUNTIME_MODE=live_llm in .env.local."
        )

    started = time.perf_counter()
    with input_path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    log.info("reformat_starting", input=str(input_path.name), records=len(records))

    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*[reformat_one(r, settings, concurrency_token=sem) for r in records])

    out_filename = output_filename or input_path.name.replace(".jsonl", ".reformatted.jsonl")
    out_path = CORPUS_REFORMATTED / out_filename
    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    kept = sum(1 for r in results if not r.skipped)
    elapsed = time.perf_counter() - started
    log.info(
        "reformat_complete",
        input=input_path.name,
        total=len(results),
        kept=kept,
        skipped=len(results) - kept,
        elapsed_s=round(elapsed, 1),
        output=out_path.name,
    )
    return out_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m reasoning.eval.corpus.reformat <path-to-raw-jsonl>", file=sys.stderr)
        sys.exit(2)
    raw = Path(sys.argv[1])
    if not raw.exists():
        # Allow relative to CORPUS_DATA
        raw = CORPUS_DATA / sys.argv[1]
    out = asyncio.run(reformat_corpus(raw))
    print(out)
