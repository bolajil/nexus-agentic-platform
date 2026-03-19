"""
NEXUS Platform — OpenTelemetry + Prometheus Observability Setup
Configures distributed tracing and metrics collection.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def setup_telemetry(app=None, enabled: bool = False, endpoint: str = "") -> None:
    """
    Initialize OpenTelemetry tracing and Prometheus metrics.
    Gracefully skips if packages are not installed.
    """
    if not enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=False)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: "nexus-backend"})
        provider = TracerProvider(resource=resource)

        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {endpoint}")
        except ImportError:
            logger.warning("OTLP exporter not available, using console exporter")
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)

        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI OpenTelemetry instrumentation enabled")
            except ImportError:
                logger.warning("FastAPI OTel instrumentor not available")

        logger.info("OpenTelemetry tracing initialized")

    except ImportError:
        logger.warning("OpenTelemetry SDK not installed — tracing disabled")


def setup_prometheus(app=None) -> None:
    """Add Prometheus metrics endpoint to FastAPI app."""
    if app is None:
        return
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            excluded_handlers=["/health", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus metrics exposed at /metrics")
    except ImportError:
        logger.warning("prometheus_fastapi_instrumentator not installed — metrics disabled")


def get_tracer(name: str = "nexus"):
    """Get an OpenTelemetry tracer."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return None
