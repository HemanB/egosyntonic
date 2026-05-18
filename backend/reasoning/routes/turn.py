"""POST /turn — the primary interaction endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth import CurrentUser
from ..config import Settings, get_settings
from ..pipeline.orchestrator import run_turn
from ..pipeline.types import TurnInput, TurnResult

router = APIRouter(tags=["turn"])


class TurnRequest(TurnInput):
    """Wire-level turn request. Mirrors TurnInput; allows future divergence."""


@router.post("/turn", response_model=TurnResult)
async def post_turn(
    request: TurnRequest,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TurnResult:
    # Override user_id from auth — never trust client-supplied user_id
    turn = TurnInput(
        user_id=user.user_id,
        session_id=request.session_id,
        utterance_text=request.utterance_text,
        client_timestamp=request.client_timestamp,
    )
    return await run_turn(turn, settings)
