"""Standard paths for corpus artifacts. All gitignored."""

from __future__ import annotations

from pathlib import Path

# backend/reasoning/eval/corpus/paths.py → parents[3] = backend/
_BACKEND = Path(__file__).resolve().parents[3]
EVAL_ROOT = _BACKEND / "eval"
CORPUS_DATA = EVAL_ROOT / "corpus" / "data"
CORPUS_REFORMATTED = EVAL_ROOT / "corpus" / "reformatted"
CORPUS_CATEGORIZED = EVAL_ROOT / "corpus" / "categorized"
RUNS = EVAL_ROOT / "runs"
REPORTS = EVAL_ROOT / "reports"

for _p in (CORPUS_DATA, CORPUS_REFORMATTED, CORPUS_CATEGORIZED, RUNS, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)
