"""Queue configuration — names, priority scoring, concurrency limits."""

from datetime import datetime, timezone
from typing import Optional

# ── Queue & Stream Names ───────────────────────────────────────────────
QUEUE_PROCESS_LECTURE = "process_lecture"
DLQ_PROCESS_LECTURE = "dlq:process_lecture"
IDEMPOTENCY_SET = "idempotency:process_lecture"

# ── Priority Scoring ───────────────────────────────────────────────────
PRIORITY_TODAY_BONUS = 1000


def compute_priority_score(created_at: Optional[datetime] = None) -> float:
    """Score for ZSET-based priority queue.

    Formula: (is_today ? 1000 : 0) + hours_since_created
    Higher score = higher priority. Workers use ZPOPMAX.
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)

    # Bonus for same-day uploads
    today_bonus = PRIORITY_TODAY_BONUS if created_at.date() == now.date() else 0

    # Age in hours (fractional)
    hours_since = (now - created_at).total_seconds() / 3600.0

    return float(today_bonus + hours_since)


# ── Concurrency Limits (defaults — overridden by Settings env vars) ─────
# Workers read their actual concurrency from Settings (env vars) at runtime.
# These constants serve as fallback defaults for standalone scripts / tests.
TRANSCRIPTION_CONCURRENCY = 3
AI_CONCURRENCY = 5
EMBEDDING_CONCURRENCY = 10