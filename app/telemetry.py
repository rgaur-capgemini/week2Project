
"""
OpenTelemetry observability configuration.
Tracks latency, token usage, vector search metrics, and errors.
Exports traces to Google Cloud Trace for production monitoring.
"""

import os
import time
from typing import Optional, Callable
from contextlib import contextmanager
from fastapi import FastAPI, Request
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

# Global tracer and meter
tracer: Optional[trace.Tracer] = None
meter: Optional[metrics.Meter] = None

# Metrics
request_counter: Optional[metrics.Counter] = None
latency_histogram: Optional[metrics.Histogram] = None
token_counter: Optional[metrics.Counter] = None
vector_search_latency: Optional[metrics.Histogram] = None
embedding_latency: Optional[metrics.Histogram] = None


def configure_otel(app: FastAPI):
    """
    Configure OpenTelemetry with Cloud Trace and Cloud Monitoring.
    """
    global tracer, meter, request_counter, latency_histogram
    global token_counter, vector_search_latency, embedding_latency
    
    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        print("Warning: PROJECT_ID not set. OpenTelemetry disabled.")
        return app
    
    # Configure resource
    resource = Resource.create({
        "service.name": "week1-rag-service",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "production")
    })
    
    # Configure tracing
    trace_exporter = CloudTraceSpanExporter(project_id=project_id)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(__name__)
    
    # Configure metrics
    metrics_exporter = CloudMonitoringMetricsExporter(project_id=project_id)
    metric_reader = PeriodicExportingMetricReader(metrics_exporter, export_interval_millis=60000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(__name__)
    
    # Create metrics
    request_counter = meter.create_counter(
        name="rag_requests_total",
        description="Total number of RAG requests",
        unit="1"
    )
    
    latency_histogram = meter.create_histogram(
        name="rag_latency_seconds",
        description="RAG request latency in seconds",
        unit="s"
    )
    
    token_counter = meter.create_counter(
        name="rag_tokens_total",
        description="Total tokens used by LLM",
        unit="1"
    )
    
    vector_search_latency = meter.create_histogram(
        name="vector_search_latency_seconds",
        description="Vector search latency in seconds",
        unit="s"
    )
    
    embedding_latency = meter.create_histogram(
        name="embedding_latency_seconds",
        description="Embedding generation latency in seconds",
        unit="s"
    )
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Add middleware for request tracking
    @app.middleware("http")
    async def track_requests(request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        latency = time.time() - start_time
        
        # Record metrics
        if request_counter:
            request_counter.add(1, {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code
            })
        
        if latency_histogram:
            latency_histogram.record(latency, {
                "method": request.method,
                "path": request.url.path
            })
        
        return response
    
    print(f" OpenTelemetry configured for project: {project_id}")
    return app


@contextmanager
def trace_operation(operation_name: str, attributes: dict = None):
    """
    Context manager for tracing operations.
    
    Usage:
        with trace_operation("embed_text", {"num_texts": 5}):
            # your code here
    """
    if not tracer:
        yield None
        return
    
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        start_time = time.time()
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise
        finally:
            duration = time.time() - start_time
            span.set_attribute("duration_seconds", duration)


def record_vector_search(duration_seconds: float, num_results: int):
    """Record vector search metrics."""
    if vector_search_latency:
        vector_search_latency.record(duration_seconds, {"operation": "search"})


def record_embedding(duration_seconds: float, num_texts: int):
    """Record embedding generation metrics."""
    if embedding_latency:
        embedding_latency.record(duration_seconds, {"num_texts": num_texts})


def record_llm_generation(duration_seconds: float, num_contexts: int):
    """Record LLM generation metrics."""
    if embedding_latency:  # Reuse embedding_latency meter for now
        embedding_latency.record(duration_seconds, {"operation": "llm_generation", "num_contexts": num_contexts})


def record_tokens(num_tokens: int, operation: str = "generate"):
    """Record token usage."""
    if token_counter:
        token_counter.add(num_tokens, {"operation": operation})

