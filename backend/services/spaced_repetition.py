"""SM-2 lite spaced-repetition scheduler.

Inputs:
  - prev: FlashcardReviewDB (latest known state for this card)
  - quality: 0 (Again) | 1 (Hard) | 2 (Good) | 3 (Easy)

Returns updated (ease_factor, interval_days, repetitions, due_at).

Rules (simplified SM-2):
  - quality 0 (Again):   reset reps to 0, interval = 1 day, ease -= 0.20
  - quality 1 (Hard):    interval *= 1.2, ease -= 0.15
  - quality 2 (Good):    standard SM-2 interval progression
  - quality 3 (Easy):    interval *= ease * 1.3, ease += 0.10
  - ease clamped to [1.3, 2.8]
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.bookmark import FlashcardReviewDB


def schedule_next(prev: FlashcardReviewDB, quality: int) -> FlashcardReviewDB:
    if quality not in (0, 1, 2, 3):
        raise ValueError(f"Invalid quality: {quality}")

    ease = prev.ease_factor
    reps = prev.repetitions
    interval = prev.interval_days

    if quality == 0:  # Again
        reps = 0
        interval = 1
        ease = max(1.3, ease - 0.20)
    elif quality == 1:  # Hard
        reps += 1
        interval = max(1, int(round((interval or 1) * 1.2)))
        ease = max(1.3, ease - 0.15)
    elif quality == 2:  # Good
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = max(1, int(round(interval * ease)))
    else:  # Easy
        reps += 1
        if reps == 1:
            interval = 3
        elif reps == 2:
            interval = 10
        else:
            interval = max(1, int(round(interval * ease * 1.3)))
        ease = min(2.8, ease + 0.10)

    now = datetime.now(timezone.utc)
    return FlashcardReviewDB(
        id=prev.id,
        user_id=prev.user_id,
        lecture_id=prev.lecture_id,
        card_index=prev.card_index,
        ease_factor=round(ease, 2),
        interval_days=interval,
        repetitions=reps,
        last_reviewed_at=now,
        due_at=now + timedelta(days=interval),
        total_reviews=prev.total_reviews + 1,
    )
