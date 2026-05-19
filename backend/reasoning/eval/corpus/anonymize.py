"""PII scrub + post-ID hashing for the eval corpus.

Run after fetch, before reformat. The reformat step itself is given
the anonymized text — we never send raw text containing usernames or
contact info to Gemini.

This is conservative pattern-matching, not perfect anonymization. The
goal is to remove the obvious deanonymization vectors. Free-text proper
nouns (real names, places) are not scrubbed by these patterns; the
reformat prompt is instructed to drop or genericize them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from ...logging_setup import get_logger

log = get_logger(__name__)


# --- Patterns ---


# Reddit usernames: /u/foo, u/foo
_USERNAME_RE = re.compile(r"\b(?:/u/|u/)[A-Za-z0-9_-]{1,32}\b")

# Subreddit references: /r/foo, r/foo — keep these (they're not PII)
# but we'll genericize them anyway for distribution-shift reasons.
_SUBREDDIT_RE = re.compile(r"\b(?:/r/|r/)([A-Za-z0-9_]{1,32})\b")

# URLs (http, https, ftp, plain markdown links)
_URL_RE = re.compile(r"(?:https?|ftp)://\S+", re.IGNORECASE)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(\s*(?:https?|ftp)://[^\)]+\)", re.IGNORECASE)

# Email
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Phone numbers (US-ish; sufficient for de-identification, not for parsing)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,2}[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"
)

# Discord-style handles (Name#1234) and @-handles
_DISCORD_RE = re.compile(r"\b[A-Za-z0-9_]{2,32}#\d{4}\b")
_AT_HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_.]{2,32}(?!\w)")


@dataclass(slots=True)
class AnonymizationReport:
    usernames_removed: int = 0
    subreddits_removed: int = 0
    urls_removed: int = 0
    emails_removed: int = 0
    phones_removed: int = 0
    handles_removed: int = 0
    raw_chars: int = 0
    anonymized_chars: int = 0
    flags: list[str] = field(default_factory=list)


def anonymize_text(text: str) -> tuple[str, AnonymizationReport]:
    report = AnonymizationReport(raw_chars=len(text))

    out = text

    # Markdown links: keep the visible label, drop the URL
    def _md_sub(m: re.Match[str]) -> str:
        return m.group(1)

    out, n = _MD_LINK_RE.subn(_md_sub, out)
    report.urls_removed += n

    # Bare URLs
    out, n = _URL_RE.subn("[url]", out)
    report.urls_removed += n

    # Reddit usernames
    out, n = _USERNAME_RE.subn("someone", out)
    report.usernames_removed += n

    # Subreddit refs (we genericize to remove community signal that leaks
    # into the conversational reformat)
    out, n = _SUBREDDIT_RE.subn("an online community", out)
    report.subreddits_removed += n

    # Email
    out, n = _EMAIL_RE.subn("[email]", out)
    report.emails_removed += n

    # Phone
    out, n = _PHONE_RE.subn("[phone]", out)
    report.phones_removed += n

    # Handles
    out, n = _DISCORD_RE.subn("someone", out)
    report.handles_removed += n
    out, n = _AT_HANDLE_RE.subn("someone", out)
    report.handles_removed += n

    # Collapse leftover whitespace
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()

    report.anonymized_chars = len(out)
    return out, report


def hash_post_id(post_id: str, *, length: int = 16) -> str:
    """Short stable hash of the Reddit post ID. Used as the persisted record key.

    We deliberately don't keep the original ID anywhere downstream — once
    the raw-corpus JSONL is the only place it appears, the deanonymization
    surface is bounded to that file.
    """
    return hashlib.sha256(post_id.encode("utf-8")).hexdigest()[:length]


def anonymize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Anonymize a RawPost dict in place — returns a NEW dict with PII scrubbed.

    The Reddit post_id is replaced by `id_hash`; raw `post_id` is dropped.
    """
    body, body_report = anonymize_text(record.get("body", ""))
    title, title_report = anonymize_text(record.get("title", ""))

    return {
        "id_hash": hash_post_id(record["post_id"]),
        "source": record.get("source", "reddit"),
        "subreddit": record["subreddit"],
        "title": title,
        "body": body,
        "created_utc": record["created_utc"],
        "score": record["score"],
        "num_comments": record["num_comments"],
        "fetched_at": record.get("fetched_at"),
        "anonymization": {
            "body": body_report.__dict__,
            "title": title_report.__dict__,
        },
    }
