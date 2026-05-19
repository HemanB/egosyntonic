"""Synthetic eval corpus pipeline.

Pulls posts from configured subreddits, anonymizes them, reformats into the
conversational journaling cadence the egosyntonic app expects, then feeds
each reformatted utterance through the live pipeline and captures outputs
for scoring.

All persisted artifacts live under `backend/eval/corpus/` and
`backend/eval/runs/` — both gitignored. Never commit raw or reformatted
third-party content.
"""
