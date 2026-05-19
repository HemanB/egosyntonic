"""Reddit fetcher for the eval corpus.

Uses asyncpraw with a 'script'-type app. Pulls posts from configured
subreddits subject to length / age / score filters. Output is JSONL of
RawPost records.

ToS compliance:
- We use the official API via PRAW (allowed for personal-script use).
- Rate limit is respected by the library.
- Requests carry a user-agent identifying the script and the operator,
  per Reddit ToS.
- No republication of fetched content — the corpus is internal eval only,
  gitignored throughout the repo.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ...config import Settings, get_settings
from ...logging_setup import get_logger
from .paths import CORPUS_DATA

log = get_logger(__name__)


# --- Data model ---


@dataclass(slots=True)
class RawPost:
    source: str  # always "reddit"
    subreddit: str
    post_id: str       # Reddit submission ID (we hash this when reformatting)
    title: str
    body: str
    created_utc: float
    score: int
    num_comments: int
    is_self: bool      # text vs link post (we only keep text)
    nsfw: bool
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# --- Fetcher ---


_DEFAULT_LISTING = "new"  # "hot" | "new" | "top"
_MIN_BODY_CHARS = 200
_MAX_BODY_CHARS = 4000
_MAX_AGE_DAYS = 365
_MIN_SCORE = 1


async def fetch_subreddit(
    subreddit_name: str,
    *,
    limit: int,
    listing: str = _DEFAULT_LISTING,
    settings: Settings | None = None,
) -> list[RawPost]:
    """Fetch up to `limit` posts from a subreddit subject to filters."""
    settings = settings or get_settings()
    if not (settings.reddit_client_id and settings.reddit_client_secret and settings.reddit_user_agent):
        raise RuntimeError(
            "Reddit credentials missing. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USER_AGENT in backend/.env.local. See README and reddit.com/prefs/apps."
        )

    import asyncpraw  # noqa: PLC0415

    reddit = asyncpraw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )

    posts: list[RawPost] = []
    cutoff = datetime.now(UTC) - timedelta(days=_MAX_AGE_DAYS)
    try:
        subreddit = await reddit.subreddit(subreddit_name)
        # Always overfetch — we discard filter-failures
        seen = 0
        target_listing = getattr(subreddit, listing)
        async for submission in target_listing(limit=limit * 4):
            seen += 1
            if not submission.is_self:
                continue
            if submission.removed_by_category:
                continue  # mod-removed
            if not submission.selftext or submission.selftext.strip().lower() == "[removed]":
                continue
            if not (_MIN_BODY_CHARS <= len(submission.selftext) <= _MAX_BODY_CHARS):
                continue
            if datetime.fromtimestamp(submission.created_utc, tz=UTC) < cutoff:
                continue
            if submission.score < _MIN_SCORE:
                continue

            posts.append(RawPost(
                source="reddit",
                subreddit=subreddit_name,
                post_id=submission.id,
                title=submission.title,
                body=submission.selftext,
                created_utc=submission.created_utc,
                score=submission.score,
                num_comments=submission.num_comments,
                is_self=submission.is_self,
                nsfw=bool(submission.over_18),
            ))
            if len(posts) >= limit:
                break

        log.info(
            "subreddit_fetch_complete",
            subreddit=subreddit_name,
            scanned=seen,
            kept=len(posts),
        )
    finally:
        await reddit.close()

    return posts


async def fetch_corpus(
    subreddits: list[str],
    *,
    per_subreddit: int,
    output_filename: str | None = None,
) -> Path:
    """Fetch posts from each subreddit in turn and write a JSONL file.

    Output path: backend/eval/corpus/data/<timestamp>__<sub1>+<sub2>.jsonl
    """
    started = time.perf_counter()
    all_posts: list[RawPost] = []
    for sub in subreddits:
        sub_posts = await fetch_subreddit(sub, limit=per_subreddit)
        all_posts.extend(sub_posts)

    if output_filename is None:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        slug = "+".join(s.replace("/", "_") for s in subreddits)
        output_filename = f"{ts}__{slug}.jsonl"

    out_path = CORPUS_DATA / output_filename
    with out_path.open("w", encoding="utf-8") as f:
        for post in all_posts:
            f.write(json.dumps(asdict(post), ensure_ascii=False) + "\n")

    elapsed = time.perf_counter() - started
    log.info(
        "corpus_fetch_complete",
        subreddits=subreddits,
        per_subreddit=per_subreddit,
        total=len(all_posts),
        elapsed_s=round(elapsed, 1),
        output=str(out_path.relative_to(out_path.parents[3])),
    )
    return out_path


def load_corpus_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python -m reasoning.eval.corpus.fetch_reddit <per_subreddit> <subreddit1> [<subreddit2> ...]",
            file=sys.stderr,
        )
        sys.exit(2)
    per = int(sys.argv[1])
    subs = sys.argv[2:]
    out = asyncio.run(fetch_corpus(subs, per_subreddit=per))
    print(out)
