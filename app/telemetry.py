from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import Settings


@dataclass
class AppMetrics:
    ingest_jobs_total: object
    ingest_job_failures_total: object
    chat_requests_total: object
    retrieval_empty_hits_total: object
    model_request_latency_ms: object
    rag_total_latency_ms: object


_metrics: Optional[AppMetrics] = None


def setup_telemetry(settings: Settings) -> None:
    global _metrics

    if not settings.otel_enabled:
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    tracer_provider = TracerProvider(resource=resource)
    metric_readers = []

    if settings.otel_exporter_otlp_endpoint:
        tracer_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(tracer_exporter))
        metric_exporter = OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        metric_readers.append(PeriodicExportingMetricReader(metric_exporter))

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=metric_readers))
    meter = metrics.get_meter(settings.otel_service_name)
    _metrics = AppMetrics(
        ingest_jobs_total=meter.create_counter("ingest_jobs_total"),
        ingest_job_failures_total=meter.create_counter("ingest_job_failures_total"),
        chat_requests_total=meter.create_counter("chat_requests_total"),
        retrieval_empty_hits_total=meter.create_counter("retrieval_empty_hits_total"),
        model_request_latency_ms=meter.create_histogram("model_request_latency_ms"),
        rag_total_latency_ms=meter.create_histogram("rag_total_latency_ms"),
    )
    HTTPXClientInstrumentor().instrument()


def instrument_fastapi(app: object) -> None:
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]


def instrument_sqlalchemy(engine: object) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine)


def get_tracer(name: str):
    return trace.get_tracer(name)


def get_metrics() -> Optional[AppMetrics]:
    return _metrics

