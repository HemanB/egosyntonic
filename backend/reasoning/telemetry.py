"""OpenTelemetry setup — Cloud Trace exporter. No-op in fixture mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .config import Settings


def configure_tracing(app: "FastAPI", settings: "Settings") -> None:
    """Wire OpenTelemetry into the FastAPI app. Safe to call in fixture mode (no-op)."""
    if not settings.otel_enabled:
        return

    # Local import to avoid pulling in the GCP exporter when otel is disabled
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter  # noqa: PLC0415
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: PLC0415

    resource = Resource.create({SERVICE_NAME: "egosyntonic-reasoning"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=settings.google_cloud_project))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


def tracer() -> trace.Tracer:
    return trace.get_tracer("egosyntonic")
