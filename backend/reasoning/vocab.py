"""Loaders for shared/vocabularies/*.json.

These vocabularies are the contract the extraction prompt binds to. They are
loaded once at startup and cached.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _resolve_vocab_dir() -> Path:
    """Find shared/vocabularies. In repo: backend/reasoning/vocab.py → ../../shared.
    In Docker: /shared (placed there by the Dockerfile). Override with
    EGOSYN_SHARED_DIR for unusual layouts.
    """
    override = os.environ.get("EGOSYN_SHARED_DIR")
    if override:
        return Path(override) / "vocabularies"

    repo_path = Path(__file__).resolve().parents[2] / "shared" / "vocabularies"
    if repo_path.exists():
        return repo_path

    docker_path = Path("/shared/vocabularies")
    if docker_path.exists():
        return docker_path

    raise RuntimeError(
        f"could not locate shared/vocabularies. Tried {repo_path} and {docker_path}. "
        f"Set EGOSYN_SHARED_DIR to override."
    )


_VOCAB_DIR = _resolve_vocab_dir()


@lru_cache(maxsize=1)
def _load_behaviors() -> dict[str, Any]:
    return json.loads((_VOCAB_DIR / "behaviors.json").read_text())


@lru_cache(maxsize=1)
def _load_network_nodes() -> dict[str, Any]:
    return json.loads((_VOCAB_DIR / "network_nodes.json").read_text())


@lru_cache(maxsize=1)
def _load_need_domains() -> dict[str, Any]:
    return json.loads((_VOCAB_DIR / "need_domains.json").read_text())


def behaviors_for_pack(condition_pack: str) -> list[dict[str, Any]]:
    """Return flat behaviors list with {id, label, description} for the prompt."""
    pack = _load_behaviors()["packs"].get(condition_pack)
    if pack is None:
        raise KeyError(f"unknown condition_pack {condition_pack!r}")
    return [
        {
            "id": b["id"],
            "label": b["label"],
            "description": b["description"],
        }
        for b in pack["behaviors"]
    ]


def network_nodes_for_pack(condition_pack: str) -> list[dict[str, Any]]:
    pack = _load_network_nodes()["packs"].get(condition_pack)
    if pack is None:
        raise KeyError(f"unknown condition_pack {condition_pack!r}")
    return [
        {
            "id": n["id"],
            "label": n["label"],
            "kind": n["kind"],
            "egosyntonic": n.get("egosyntonic", False),
        }
        for n in pack["nodes"]
    ]


def need_domains() -> list[dict[str, Any]]:
    return _load_need_domains()["domains"]


def all_behavior_ids(condition_pack: str) -> set[str]:
    return {b["id"] for b in behaviors_for_pack(condition_pack)}


def all_node_ids(condition_pack: str) -> set[str]:
    return {n["id"] for n in network_nodes_for_pack(condition_pack)}
