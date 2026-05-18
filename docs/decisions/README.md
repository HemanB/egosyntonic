# Architecture Decision Records

Lightweight ADRs capturing decisions that change the original plan (in `~/.claude/plans/wondrous-stirring-brooks.md`) or resolve open questions in `docs/idea.md` §14.

## Format

```
docs/decisions/NNN-short-title.md

# NNN — Short title

**Status:** proposed | accepted | superseded by NNN
**Date:** YYYY-MM-DD
**Deciders:** names

## Context
What was the situation that called for a decision?

## Decision
What did we choose?

## Consequences
What follows from this choice — what becomes easier, what becomes harder?
```

ADRs are append-only. To revisit a decision, write a new ADR that supersedes the prior one rather than editing history.
