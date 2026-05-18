"""FastAPI app factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from . import __version__
from .config import get_settings
from .logging_setup import configure_logging, get_logger
from .routes import health, turn
from .telemetry import configure_tracing

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info(
        "starting",
        version=__version__,
        runtime_mode=settings.runtime_mode.value,
        dev_auth_bypass=settings.dev_auth_bypass,
    )
    yield
    log.info("shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="egosyntonic reasoning",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(turn.router)
    configure_tracing(app, settings)
    return app


app = create_app()
