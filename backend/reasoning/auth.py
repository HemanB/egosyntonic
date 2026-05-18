"""Firebase Auth ID token verification with dev-bypass mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from .config import Settings, get_settings
from .logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AuthedUser:
    user_id: str
    email: str | None = None
    is_dev_bypass: bool = False


_firebase_initialized = False


def _ensure_firebase_initialized(settings: Settings) -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return
    if settings.is_fixture or settings.dev_auth_bypass:
        return

    # Import lazily so fixture-mode unit tests don't need firebase-admin's network deps
    import firebase_admin  # noqa: PLC0415
    from firebase_admin import credentials  # noqa: PLC0415

    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
    _firebase_initialized = True


def authenticate(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthedUser:
    """Verify the bearer token and return the authenticated user.

    In fixture mode or when EGOSYN_DEV_AUTH_BYPASS=true, returns a bypass user.
    """
    if settings.dev_auth_bypass or settings.is_fixture:
        return AuthedUser(user_id=settings.dev_bypass_user_id, is_dev_bypass=True)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="empty bearer token",
        )

    _ensure_firebase_initialized(settings)
    from firebase_admin import auth as fb_auth  # noqa: PLC0415

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as exc:
        log.warning("auth_token_verification_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        ) from exc

    return AuthedUser(
        user_id=str(decoded["uid"]),
        email=decoded.get("email"),
    )


CurrentUser = Annotated[AuthedUser, Depends(authenticate)]
