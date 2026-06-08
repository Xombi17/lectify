"""
Custom Prometheus metrics for the Lectify application.

Initialize at module import time — Prometheus registers them in the default registry
which the Instrumentator exposes at /metrics.

All metric names use the "lectify_" prefix to avoid naming collisions.
All labels are bounded (no user_id, lecture_id, or other high-cardinality values).
"""

from prometheus_client import Counter, Gauge, Histogram

# ── Lecture Processing ──────────────────────────────────────
lectures_uploaded = Counter(
    "lectify_lectures_uploaded_total",
    "Total number of lectures uploaded",
    ["source"],  # "live_mic" | "file_upload"
)

lectures_processed = Counter(
    "lectify_lectures_processed_total",
    "Total number of lectures fully processed (status=ready)",
    ["status"],  # "success" | "failed"
)

active_lectures = Gauge(
    "lectify_active_lectures",
    "Number of lectures currently being processed (queued + in-progress)",
)

# ── AI Pipeline ─────────────────────────────────────────────
ai_generation_duration = Histogram(
    "lectify_ai_generation_duration_seconds",
    "Duration of AI generation calls (summary, notes, quiz, etc.)",
    ["task_type"],  # "summary" | "notes" | "quiz" | "flashcards" | "transcription"
    buckets=(1, 2, 5, 10, 15, 30, 60, 120),
)

ai_generation_tokens = Counter(
    "lectify_ai_generation_tokens_total",
    "Total tokens consumed by AI generation",
    ["task_type", "model"],
)


def record_lecture_uploaded(source: str) -> None:
    """Call from the upload route handler when a lecture file is received."""
    lectures_uploaded.labels(source=source).inc()
    active_lectures.inc()


def record_lecture_processed(status: str) -> None:
    """Call after a lecture finishes processing pipeline."""
    lectures_processed.labels(status=status).inc()
    active_lectures.dec()


# ── Queue Metrics (Phase 7 instruments queue_client.py) ──────────────
queue_depth = Gauge(
    "lectify_queue_depth",
    "Current number of items waiting in each queue",
    ["queue_type"],  # "process_lecture"
)

queue_processing_duration = Histogram(
    "lectify_queue_processing_duration_seconds",
    "Duration of job processing from first dequeued to completed/failed",
    ["queue_type", "status"],  # status: "success" | "failed"
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

queue_failures = Counter(
    "lectify_queue_failures_total",
    "Total number of failed jobs",
    ["queue_type", "failure_reason"],  # "timeout" | "error" | "max_retries_exceeded"
)

queue_latency = Histogram(
    "lectify_queue_latency_seconds",
    "Time a job spends in queue before processing starts",
    ["queue_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800),
)

dead_letter_depth = Gauge(
    "lectify_dead_letter_depth",
    "Number of items in the dead-letter queue",
    ["queue_type"],
)

queue_retry_count = Counter(
    "lectify_queue_retries_total",
    "Total number of job retries across all queues",
    ["queue_type"],
)
