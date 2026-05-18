"""The 4-head CoT reasoning pipeline.

Pipeline stages (idea.md §3.1):

    extraction → retrieval → reasoning → generation → critic → state

Each stage is a module with a single async entry point. The orchestrator
wires them together for a single user turn.
"""
