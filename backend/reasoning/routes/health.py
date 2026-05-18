"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "runtime_mode": settings.runtime_mode.value,
    }


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}
