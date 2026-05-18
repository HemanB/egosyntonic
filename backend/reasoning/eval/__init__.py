"""Eval harness — runs golden fixtures against the live pipeline.

Phase 1 exit verification (Task #11) lives here. Each fixture in
`backend/eval/golden/` is loaded, fed through the pipeline, and checked
against its expected-output assertions.
"""
